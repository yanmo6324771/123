import os

MOD_LIST = []
MOD_CONFIG_DICT = []


def list_mod():
    global MOD_LIST
    if not MOD_LIST:
        MOD_LIST = []
        for dir_name in os.listdir('./submodule'):
            mod_path = os.path.join('./submodule', dir_name)
            if os.path.isdir(mod_path):
                for file_name in os.listdir(mod_path):
                    mod_name, ext = os.path.splitext(file_name)
                    if ext == '.py':
                        MOD_LIST.append((mod_name, dir_name))

    return MOD_LIST


def get_dir_name(name):
    for mod_name, dir_name in list_mod():
        if name == mod_name:
            return dir_name


def filepath_mod(name):
    return os.path.join('./submodule', get_dir_name(name))


def mod_template():
    out = []
    for mod_name, dir_name in list_mod():
        for file in os.listdir(os.path.join('./submodule', dir_name, 'config')):
            name, extension = os.path.splitext(file)
            if name == 'template' and extension == '.json':
                out.append(name)

    return out


def mod_instance():
    global MOD_CONFIG_DICT
    MOD_CONFIG_DICT = {}
    out = []
    for mod_name, dir_name in list_mod():
        for file in os.listdir(os.path.join('./submodule', dir_name, 'config')):
            name, extension = os.path.splitext(file)
            if name != 'template' and extension == '.json':
                out.append(name)
                MOD_CONFIG_DICT[name] = mod_name

    return out


def get_config_mod(config_name):
    try:
        return MOD_CONFIG_DICT[config_name]
    except KeyError:
        return 'alas'
