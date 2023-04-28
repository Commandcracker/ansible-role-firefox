import re


def read_all_user_prefs(pref_file_path):
    with open(pref_file_path, 'r') as f:
        contents = f.read()
        pattern = r'user_pref\("(.*?)"\s*,\s*(.*?)\);'
        matches = re.findall(pattern, contents)
        return dict(matches)


"""
'/home/red/narsil.js'
/home/red/arkenfox.js

/home/red/Betterfox.js
/home/red/Fastfox.js
/home/red/Peskyfox.js
/home/red/Securefox.js
/home/red/Smoothfox.js
"""

pref_dict = read_all_user_prefs(
    '/home/red/Fastfox.js'
)
for pref_key, pref_value in pref_dict.items():
    print(f"{pref_key}: {pref_value}")
