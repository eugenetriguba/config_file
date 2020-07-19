import toml

from config_file.nested_lookup import (
    get_occurrence_of_key,
    nested_delete,
    nested_lookup,
    nested_update,
)
from config_file.exceptions import ParsingError
from config_file.parsers import BaseParser, parse_value
from config_file.utils import split_on_dot


class TomlParser(BaseParser):
    """The TomlParser allows use of toml files with ConfigFile."""

    def __init__(self, file_contents: str):
        """Reads in the file contents into the parser."""
        super().__init__(file_contents)

    def parse(self, file_contents: str):
        try:
            return toml.loads(file_contents)
        except toml.TomlDecodeError as error:
            raise ParsingError(error)

    def get(self, key: str, parse_types: bool = False, all: bool = False):
        """
        Retrieve values using a dot syntax.

        :param key: The key to retrieve. e.g. 'foo.bar.boo'

        :param parse_types: Whether you'd like the type parsed into its native one.

        :param all: Specify whether you'd like to recursively receive
        all values that match the given key. Returned as a list.
        e.g. 'foo' would retrieve all values that have the key 'foo', anywhere
        in the json.

        :return: the value of the given key
        """
        if all:
            result = nested_lookup(key, self.parsed_content)
        elif "." in key:
            split_keys = split_on_dot(key)
            result = self.parsed_content

            # Used so we can more precisely specify what key is causing the error.
            key_for_error = None
            try:
                for key in split_keys:
                    key_for_error = key
                    result = result[key]
            except TypeError:
                raise ParsingError(
                    f"Cannot get {key} because {key_for_error} is not subscriptable."
                )
        else:
            result = self.parsed_content[key]

        return parse_value(result) if parse_types else result

    def set(self, key: str, value, all: bool = False):
        if all:
            nested_update(self.parsed_content, key, value, in_place=True)
        elif "." in key:
            indexes = split_on_dot(key)
            indexes_length = len(indexes)

            ref = self.parsed_content
            for index, key in enumerate(indexes):
                if index == indexes_length - 1:
                    ref[key] = value
                    break

                ref = ref[key]
        else:
            self.parsed_content[key] = value

        return True

    def delete(self, key, all: bool = False):
        if all:
            nested_delete(self.parsed_content, key, in_place=True)
        elif "." in key:
            indexes = split_on_dot(key)
            indexes_length = len(indexes)

            ref = self.parsed_content
            for index, key in enumerate(indexes):
                if index == indexes_length - 1:
                    del ref[key]
                    break

                ref = ref[key]
        else:
            del self.parsed_content[key]

        return True

    def stringify(self) -> str:
        return json.dumps(self.parsed_content, indent=4)

    def has(self, search_key: str) -> bool:
        return get_occurrence_of_key(self.parsed_content, key=search_key) > 0
