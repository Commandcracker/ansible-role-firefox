#!/usr/bin/python

# TODO: add support for external extensions (url to xpi file)
# TODO: install themes

# Built-in modules
from json import loads
from os import makedirs, remove
from os.path import (
    join,
    basename,
    dirname,
    isfile
)
from urllib.request import urlopen
from urllib.parse import urlparse
from shutil import move
from tempfile import mkdtemp

# External modules
from ansible.module_utils.basic import AnsibleModule


class DownloadError(Exception):
    def __init__(self, slug: str, url: str, status_code: int) -> None:
        self.message = (
            f"Could not download {slug} from {url}. "
            f"Status code: {status_code}"
        )
        super().__init__(self.message)


class FirefoxExtension:
    def __init__(self, slug: str, profile_path: str):
        self.slug = slug
        self.profile_path = profile_path
        self.info: dict = None
        self.id: str = None
        self.guid: str = None
        self.url: str = None
        self.filename: str = None
        self.download_path: str = None
        self.destination: str = None
        self._post_init__()

    def _get_info(self) -> dict:
        url = f"https://services.addons.mozilla.org/api/v4/addons/addon/{self.slug}"
        with urlopen(url) as response:
            if response.status != 200:
                raise DownloadError(self.slug, url, response.status)
            info = loads(response.read())
        return info

    def _post_init__(self):
        self.info = self._get_info()
        self.id = self.info.get("id")
        self.guid = self.info["guid"]
        self.url = self.info["current_version"]["files"][0]["url"]
        self.filename = basename(urlparse(self.url).path)
        self.download_path = join(mkdtemp(), self.filename)
        self.destination = join(
            self.profile_path,
            "extensions",
            f"{self.guid}.xpi"
        )

    def _download(self):
        response = urlopen(self.url)
        if response.status != 200:
            raise DownloadError(self.slug, self.url, response.status)
        with open(self.download_path, "wb") as file:
            while True:
                chunk = response.read(1024)
                if not chunk:
                    break
                file.write(chunk)

    def is_installed(self):
        return isfile(self.destination)

    def install(self):
        makedirs(dirname(self.destination), mode=0o700, exist_ok=True)
        self._download()
        move(self.download_path, self.destination)

    def uninstall(self):
        remove(self.destination)


def install_or_uninstall_addon(state: str, addon: FirefoxExtension) -> dict:
    if state == "present" and not addon.is_installed():
        addon.install()
        return {
            "changed": True,
            "meta": {
                "id": addon.id,
                "url": addon.url,
                "name": addon.filename
            }
        }

    if state == "absent" and addon.is_installed():
        addon.uninstall()
        return {"changed": True}

    return {"changed": False}


def main() -> None:
    fields = {
        "name": {"required": True, "type": "str"},
        "profile_path": {"required": True, "type": "str"},
        "state": {
            "default": "present",
            "choices": ["present", "absent"],
            "type": "str",
        },
    }
    module = AnsibleModule(argument_spec=fields)
    profile_path = module.params["profile_path"]

    addon = FirefoxExtension(module.params["name"], profile_path)
    state = module.params["state"]

    try:
        result = install_or_uninstall_addon(state, addon)
        module.exit_json(**result)
    except Exception as exception:
        module.fail_json(msg=str(exception))


if __name__ == "__main__":
    main()
