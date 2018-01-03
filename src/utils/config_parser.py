#-*- coding: utf-8 -*-

import ConfigParser
from os.path import expanduser

def ConfigSectionMap(section):
    home = expanduser('~')

    Config = ConfigParser.ConfigParser()
    Config.read(home + '/.hmcnf')

    config_dic = {}
    try:
        options = Config.options(section)
    except:
        return None

    for option in options:
        try:
            config_dic[option] = Config.get(section, option)
            if config_dic[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print 'exception on %s!' % option
            config_dic[option] = None
    return config_dic