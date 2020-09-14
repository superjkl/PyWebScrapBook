import os, json
from collections import OrderedDict
from .util import (
    remove_prefix,
    remove_suffix,
    remove_lines,
    parse_json,
    Memoize,
    find_regex_file,
    get_filename_no_ext,
    get_number_suffix,
    SimpleObject
)


class Files:

    # Constants
    TOC_REGEX  = str(r"^toc([0-9]*)\.js$")
    META_REGEX = str(r"^meta([0-9]*)\.js$")

    FILE_COMMENT = "/** \n * Feel free to edit this file, but keep data code valid JSON format.\n */\n"
    
    TOC_PREFIX   = "scrapbook.toc("
    META_PREFIX  = "scrapbook.meta("
    
    TOC_SUFFIX   = ")"
    META_SUFFIX  = TOC_SUFFIX


    def __init__(self, scrapbook_dir):
        self._scrapbook_dir = os.path.expanduser(scrapbook_dir)
        self._tree_dir      = os.path.join(self._scrapbook_dir, 'tree/')
        self._valid_scrapbook_dir()

        self.files = SimpleObject()
        self.files.toc  = ''
        self.files.meta = ''
        self.load_files()

    def _valid_scrapbook_dir(self):
        ''' 
        raises exceptions if scrapbook directory is invalid and get filepaths for necessary files
        '''
        try:
            os.path.isdir(self._tree_dir)
        except:
            raise Exception('Current working directory is not a scrapbook directory')


    def write_toc(self, toc: dict):
        # def backup_toc():
        # # TODO: improve backup
        #     try:
        #         os.rename(self._toc_file, self._toc_file + '.bak')
        #     except:
        #         raise Exception('Could not backup ' + self._toc_file + ' before writing')

        # def write_new_toc(toc):
        #     def toc_preprocessing(toc):
        #         return self.FILE_COMMENT + self.TOC_PREFIX + json.dumps(toc) + self.TOC_SUFFIX
        #     with open(self._toc_file, "w") as file:
        #         file.write(
        #             toc_preprocessing(json.dumps(toc))
        #         )
        # backup_toc()
        # write_new_toc(toc)
        pass


    # Parse and load files
    ###############################################################################

    @staticmethod
    def _json_preprocessing(comment_lines, prefix, suffix):
        def preprocessing(file):
            remove_lines(file, comment_lines)
            return remove_suffix(
                        remove_prefix(file.read().strip(), prefix), suffix)
        return preprocessing


    @staticmethod
    def _get_merged_dictionaries_on_filename_precedence(directory, regex, no_match_message, load_func):
        '''
            merge all files in directory which match the glob and 
            merge them in order of highest number before the file extension first
        '''
        def sort_files_by_number(file_filenumbers):
            ''' large numbers later so they are merged later with precedence '''
            file_filenumbers.sort(key= lambda f: f[1])

        def merge_files(files):
            ''' load each file at a time and merge top level keys into single dictionary '''
            dictionary = dict()
            for file in files:
                file_dict = load_func(file)
                dictionary = { **dictionary , **file_dict }
            return dictionary

        file_filenames = [ (file, get_filename_no_ext(file)) for file in find_regex_file(directory, regex, no_match_message) ]
        file_filenumbers = [ (file, get_number_suffix(filename)) for file, filename in file_filenames ]
        sort_files_by_number(file_filenumbers)
        ordered_files = [f[0] for f in file_filenumbers]
        return merge_files(ordered_files)
    
    def _load_toc(self):
        def _load_toc_file(file):
            return parse_json(file,
                            self._json_preprocessing(3, self.TOC_PREFIX, self.TOC_SUFFIX))
        self.files.toc = self._get_merged_dictionaries_on_filename_precedence(
            self._tree_dir,
            self.TOC_REGEX,
            'No toc file found in scrapbook directory matching the glob: ' + self.TOC_REGEX,
            _load_toc_file)

    def _load_meta(self):
        def _load_meta_file(file):
            return parse_json(file,
                            self._json_preprocessing(3, self.META_PREFIX, self.META_SUFFIX))
        self.files.meta = self._get_merged_dictionaries_on_filename_precedence(
            self._tree_dir,
            self.META_REGEX,
            'No toc file found in scrapbook directory matching the glob: ' + self.META_REGEX,
            _load_meta_file)
        
    def load_files(self):
        ''' load all necessary files for scrapbook '''
        self._load_toc()
        self._load_meta()