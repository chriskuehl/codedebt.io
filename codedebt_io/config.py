import configparser
import os


base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config = configparser.ConfigParser()
config.read(os.environ.get(
    'CODEDEBT_SETTINGS',
    os.path.join(base_path, 'settings.cfg'),
))
