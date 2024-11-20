class VideoConfig:
    enabled = False
    path = None
    output_pattern = None
    
    def __init__(self, config_dict:dict):
        self.enabled = config_dict['enabled'] if 'enabled' in config_dict else False
        self.path = config_dict['path'] if 'path' in config_dict else None
        self.output_pattern = config_dict['output_pattern'] if 'output_pattern' in config_dict else None
        
    def __init__(self, enabled, path, output_pattern):
        self.enabled = enabled
        self.path = path
        self.output_pattern = output_pattern