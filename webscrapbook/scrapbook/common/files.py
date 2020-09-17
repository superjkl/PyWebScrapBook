import os, json, re
from collections import OrderedDict
from itertools import count
from .util import (
    remove_prefix,
    remove_suffix,
    remove_lines,
    parse_json,
    Memoize,
    find_regex_file,
    write_file,
    delete_file,
    file_exists,
    get_number_suffix,
    SimpleObject,
    merge_dictionaries,
    split_dictionary
)


class Files:

    def __init__(self, scrapbook_dir):
        self.__set_file_constants()

        self.__scrapbook_dir = os.path.expanduser(scrapbook_dir)
        self.__tree_dir      = os.path.join(self.__scrapbook_dir, 'tree/')
        
        self.__valid_scrapbook_dir()
        self.load_files()


    def __set_file_constants(self):
        # Constants
        self.__constants = SimpleObject()

        self.__constants.TOC_REGEX      = str(r"^toc([0-9]*)\.js$")
        self.__constants.META_REGEX     = str(r"^meta([0-9]*)\.js$")
        self.__constants.FULLTEXT_REGEX = str(r"^fulltext([0-9]*)\.js$")

        self.__constants.TOC_TEMPLATE      = str("toc{}.js")
        self.__constants.META_TEMPLATE     = str("meta{}.js")
        self.__constants.FULLTEXT_TEMPLATE = str("fulltext{}.js")

        # .+? is .+ that matches the fewest characters, ? makes the .+ non-greedy
        # [\s\S] matches any character
        # TODO: this will wrongly match if '})' is found after the actual json content
        self.__constants.FILE_CONTENT_REGEX      = str(r"scrapbook\..+?\((\{[\s\S]*\})\)")

        self.__constants.TOC_CONTENT_TEMPLATE      = "/**\n * Feel free to edit this file, but keep data code valid JSON format.\n */\nscrapbook.toc({})"
        self.__constants.META_CONTENT_TEMPLATE     = "/**\n * Feel free to edit this file, but keep data code valid JSON format.\n */\nscrapbook.meta({})"
        self.__constants.FULLTEXT_CONTENT_TEMPLATE = "/**\n * This file is generated by WebScrapBook and is not intended to be edited.\n */\nscrapbook.fulltext({})"

        self.files = SimpleObject()


    def __valid_scrapbook_dir(self):
        ''' 
        raises exceptions if scrapbook directory is invalid and get filepaths for necessary files
        '''
        if not os.path.isdir(self.__tree_dir):
            raise Exception(self.__tree_dir + ' is not a scrapbook directory')


    # Parse and load files
    ###############################################################################

    @staticmethod
    def __json_preprocessing(FILE_CONTENT_REGEX):
        def preprocessing(file):
            text = file.read()
            m = re.search(FILE_CONTENT_REGEX, text)
            if m:
                return  m.group(1)
            else:
                raise Exception("Json content not found in tree file.")
        return preprocessing


    @staticmethod
    def __get_merged_files(directory, regex, no_match_message, load_func):
        '''
            Merge contents of many files into a single dictionary.
            Merge all files in directory which match the regex.
            Files are merged where higher number files have a higher precedence.
        '''
        def get_filename_no_ext(filepath):
            return os.path.splitext(os.path.basename(filepath))[0]

        def sort_files_by_number(file_filenumbers):
            ''' large numbers later so they are merged later with precedence '''
            file_filenumbers.sort(key= lambda f: f[1])

        file_filenames = [(file, get_filename_no_ext(file)) for file in find_regex_file(directory, regex, no_match_message)]
        file_filenumbers = [(file, get_number_suffix(filename)) for file, filename in file_filenames]
        sort_files_by_number(file_filenumbers)
        ordered_files = [f[0] for f in file_filenumbers]
        file_dictionaries = [load_func(file) for file in ordered_files]
        return merge_dictionaries(file_dictionaries)
    
    def __load_toc(self):
        def load_toc_file(file):
            return parse_json(file,
                            self.__json_preprocessing(self.__constants.FILE_CONTENT_REGEX))
        self.files.toc = self.__get_merged_files(
            self.__tree_dir,
            self.__constants.TOC_REGEX,
            'No toc file found in scrapbook directory matching the regex: ' + self.__constants.TOC_REGEX,
            load_toc_file)

    def __load_meta(self):
        def load_meta_file(file):
            return parse_json(file,
                            self.__json_preprocessing(self.__constants.FILE_CONTENT_REGEX))
        self.files.meta = self.__get_merged_files(
            self.__tree_dir,
            self.__constants.META_REGEX,
            'No toc file found in scrapbook directory matching the regex: ' + self.__constants.META_REGEX,
            load_meta_file)

    def __load_fulltext(self):
        def load_fulltext_file(file):
            return parse_json(file,
                            self.__json_preprocessing(self.__constants.FILE_CONTENT_REGEX))
        self.files.fulltext = self.__get_merged_files(
            self.__tree_dir,
            self.__constants.FULLTEXT_REGEX,
            'No fulltext file found in scrapbook directory matching the regex: ' + self.__constants.FULLTEXT_REGEX,
            load_fulltext_file)
        
    def load_files(self):
        ''' load all necessary files for scrapbook '''
        self.__load_toc()
        self.__load_meta()
        self.__load_fulltext()


    # Write files
    ###############################################################################

    def __write_split_files(self, dictionary: dict, max_size, FILENAME_FORMAT, preprocessing=lambda x:x):
        '''
            Split dictionary and write each portion to a separate numbered file.
            After writing the files, delete stale numbered files
        '''
        def write_split_files(dictionaries):
            for i, dictionary  in enumerate(dictionaries):
                write_file(
                    self.__tree_dir,
                    FILENAME_FORMAT.format(i if i != 0 else ''),
                    preprocessing(json.dumps(dictionary, indent=' '))
                )

        def delete_old_split_files(start_num):
            ''' start deleting numbered files from given start_num '''
            for i in count(start_num):
                if file_exists(self.__tree_dir, FILENAME_FORMAT.format(i)):
                    delete_file(self.__tree_dir, FILENAME_FORMAT.format(i))
                else:
                    break

        dictionaries = split_dictionary(dictionary, max_size)
        write_split_files(dictionaries)
        # wrote [0,len(dictionary)-1] files so delete [len(dictionary),∞] files
        delete_old_split_files(len(dictionaries))


    def write_toc(self):
        def toc_preprocessing(string):
                return self.__constants.TOC_CONTENT_TEMPLATE.format(string)
        
        # A javascript string >= 256 MiB (UTF-16 chars) causes an error
        # in the browser. Split each js file at around 4 M entries to
        # prevent the issue. (An entry is mostly < 32 bytes)
        max_size = 4 * 1024 * 1024
        self.__write_split_files(
            self.files.toc,
            max_size,
            self.__constants.TOC_TEMPLATE,
            toc_preprocessing
        )

    def write_meta(self):
        def meta_preprocessing(string):
                return self.__constants.META_CONTENT_TEMPLATE.format(string)
        
        # A javascript string >= 256 MiB (UTF-16 chars) causes an error
        # in the browser. Split each js file at around 256 K items to
        # prevent the issue. (An item is mostly < 512 bytes)
        max_size = 256 * 1024
        self.__write_split_files(
            self.files.meta,
            max_size,
            self.__constants.META_TEMPLATE,
            meta_preprocessing
        )

    def write_fulltext(self, toc: dict):
        # TODO: implement get max_size
        # def toc_preprocessing(string):
        #         return self.__constants.FULLTEXT_CONTENT_TEMPLATE.format(string)
        
        # # A javascript string >= 256 MiB (UTF-16 chars) causes an error
        # # in the browser. Split each js file at around 4 M entries to
        # # prevent the issue. (An entry is mostly < 32 bytes)
        # max_size = 4 * 1024 * 1024
        # self.__write_split_files(
        #     toc,
        #     max_size,
        #     self.__constants.FULLTEXT_TEMPLATE,
        #     toc_preprocessing
        # )
        pass

    def write_files(self):
        self.write_toc()
        self.write_meta()