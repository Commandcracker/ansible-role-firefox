#!/usr/bin/python

# Built-in modules
from collections import OrderedDict
from configparser import RawConfigParser, ConfigParser
from io import TextIOBase
from os.path import join, expanduser
from shutil import rmtree
from subprocess import Popen, PIPE

# External modules
from ansible.module_utils.basic import AnsibleModule


class FirefoxConfigWrapper:
    """Wrapper around file object to remove spaces around .ini file delimiters.

    Taken from http://stackoverflow.com/a/25084055.
    """

    output_file: TextIOBase

    def __init__(self, new_output_file: TextIOBase):
        self.output_file = new_output_file

    def write(self, what: str) -> None:
        self.output_file.write(what.replace(" = ", "="))


class FirefoxFailedToCreateProfileError(Exception):
    def __init__(self, stderr: str, returncode: int) -> None:
        self.message = (
            f"Failed to create Firefox profile. "
            f"Return code: {returncode}. "
            f"Error message: {stderr.decode('utf-8').strip()}"
        )
        super().__init__(self.message)


class FirefoxProfiles:
    """Class to manage firefox profiles."""

    def __init__(self, path: str):
        self.path = expanduser(path)
        self.profiles_ini = join(self.path, "profiles.ini")
        self.config = RawConfigParser()
        # Make options case sensitive
        self.config.optionxform = str
        self.read()

    def read(self):
        self.config.read(self.profiles_ini)
        self.sections = OrderedDict()
        for section in self.config.sections():
            if section.startswith("Profile"):
                profile = dict(self.config.items(section))
                self.sections[profile["Name"]] = section

    def write(self):
        # Reorder the current sections, otherwise firefox deletes them on start.
        config_parser = ConfigParser()
        config_parser.optionxform = str
        config_parser.add_section("General")
        for item in self.config.items("General"):
            config_parser.set("General", item[0], item[1])

        index = 0
        for section in self.sections.values():
            new_section = f"Profile{index}"
            config_parser.add_section(new_section)
            for item in self.config.items(section):
                config_parser.set(new_section, item[0], item[1])
            index += 1

        with open(self.profiles_ini, "wb") as config_file:
            config_parser.write(FirefoxConfigWrapper(config_file))

        # Update state with the new file.
        self.read()

    def get(self, name: str) -> dict:
        if name in self.sections:
            return dict(self.config.items(self.sections[name]))

    def get_path(self, name: str) -> str:
        profile = self.get(name)
        if profile is not None:
            if (bool(profile["IsRelative"])):
                return join(self.path, profile["Path"])
            return profile["Path"]

    def delete(self, name: str) -> None:
        profile = self.get(name)
        if profile is not None:
            rmtree(self.get_path(name))
            self.sections.pop(name)
            self.write()

    def create(self, name: str) -> None:
        command = f"firefox --headless -no-remote -CreateProfile {name}"
        process = Popen(
            command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE
        )
        (stdout, stderr) = process.communicate()
        if process.returncode != 0:
            raise FirefoxFailedToCreateProfileError(stderr, process.returncode)
        self.read()


def create_or_delete_profile(name: str, state: str, profiles: FirefoxProfiles) -> bool:
    if state == "present" and profiles.get(name) is None:
        profiles.create(name)
        return True

    if state == "absent" and profiles.get(name) is not None:
        profiles.delete(name)
        return True

    return False


def main() -> None:
    fields = {
        "name": {"required": True, "type": "str"},
        "path": {"default": "~/.mozilla/firefox", "type": "str"},
        "state": {
            "default": "present",
            "choices": ["present", "absent"],
            "type": "str",
        },
    }
    module = AnsibleModule(argument_spec=fields)

    name = module.params["name"]
    state = module.params["state"]
    profiles = FirefoxProfiles(module.params["path"])

    changed = create_or_delete_profile(name, state, profiles)
    module.exit_json(
        changed=changed,
        profile_name=name,
        profile_path=profiles.get_path(name)
    )


if __name__ == "__main__":
    main()
