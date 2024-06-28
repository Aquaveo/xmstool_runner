"""HelpFinder class."""

__copyright__ = "(C) Copyright Aquaveo 2020"
__license__ = "All rights reserved"

# 1. Standard python modules
import os
from urllib.request import urlopen

# 2. Third party modules
import orjson

# 3. Aquaveo modules
from xms.api.dmi import XmsEnvironment as XmEnv

# 4. Local modules


class HelpFinder:
    """Used to find the URL to a help page."""
    def __init__(self):
        """Initializes the class, sets up the ui, and loads the simulation."""

    @staticmethod
    def help_url(dialog_help_url, identifier, default, category):
        """Returns the wiki help url associated with an identifier.

        Args:
            dialog_help_url (str): 'https://www.xmswiki.com/wiki/GMS:GMS_10.5_Dialog_Help' etc.
            identifier (str): The second part of the wiki help line on the above page (after the '|').
            default (str): The help page to return if the identifier isn't found.
            category (str): Short identifier for the dialog help page

        Returns:
            See description.
        """
        url = HelpFinder._read_from_json(category, identifier)
        if not url:
            url = HelpFinder._url_from_wiki(dialog_help_url, identifier, category)
        if not url:
            url = default
        return url

    @staticmethod
    def _find_nth(haystack, needle, n):
        """Returns the nth occurrence of the substring 'needle' in the string 'haystack'.

        https://stackoverflow.com/questions/1883980

        Args:
            haystack (str): The string to search.
            needle (str): The substring we're looking for.
            n (int): Which occurrence.

        Returns:
            See description.
        """
        start = haystack.find(needle)
        while start >= 0 and n > 1:
            start = haystack.find(needle, start + len(needle))
            n -= 1
        return start

    @staticmethod
    def _url_from_wiki(dialog_help_url, identifier, category):
        """Searches the web page at dialog_help_url for the identifier and returns the corresponding URL.

        Args:
            dialog_help_url (str): 'https://www.xmswiki.com/wiki/GMS:GMS_10.5_Dialog_Help' etc.
            identifier (str): The second part of the wiki help line on the above page (after the '|').
            category (str): Short identifier for the dialog help page

        Returns:
            See description.
        """
        all_urls = HelpFinder._parse_wiki_help(dialog_help_url)
        pos = HelpFinder._find_nth(dialog_help_url, '/', 3)
        if pos < 0:
            return ''
        full_urls = {}
        for id_key, url in all_urls.items():  # Convert to full URLs
            if url.lower().startswith('http://') or url.lower().startswith('https://'):
                full_urls[id_key] = url
            else:
                full_urls[id_key] = f'{dialog_help_url[:pos]}{url}'
        if full_urls:  # Write to JSON so we don't have to parse the wiki page again
            HelpFinder._write_to_json(category, full_urls)
        return full_urls.get(identifier, '')

    @staticmethod
    def _parse_wiki_help(dialog_help_url):
        """Parses the wiki page containing the list of dialog help URLs and returns the URL for the identifier.

        Args:
            dialog_help_url (str): 'https://www.xmswiki.com/wiki/GMS:GMS_10.5_Dialog_Help' etc.

        Returns:
            (dict): Mapping of identifiers to URLs parsed from the wiki page
        """
        found_urls = {}
        try:
            with urlopen(dialog_help_url) as f:
                content = f.read().decode('utf-8')

            if content:
                list_start = '<li><a href='
                list_start_len = len(list_start)
                list_start_external_link = '<li><a rel="nofollow" class="external text" href='
                list_start_len_external_link = len(list_start_external_link)
                external_link, link_begin, last_identifier = _find_next_link(
                    content, list_start, list_start_external_link
                )
                while last_identifier:
                    url_begin = link_begin + (list_start_len_external_link if external_link else list_start_len) + 1
                    url_end = content.find('"', url_begin)
                    url = content[url_begin:url_end]
                    found_urls[last_identifier] = url
                    link_end = content.find('</li>', link_begin)
                    external_link, link_begin, last_identifier = _find_next_link(
                        content, list_start, list_start_external_link, link_end
                    )
        except Exception:
            pass

        return found_urls

    @staticmethod
    def _json_filename(category):
        """Returns the json filename where the help url is saved.

        Args:
            category (str): Short identifier for the dialog help page

        Returns:
            See description.
        """
        temp_dir = XmEnv.xms_environ_temp_directory()
        return os.path.join(temp_dir, f'{category}_help.json')

    @staticmethod
    def _read_from_json(category, identifier):
        """Returns the help_url in the help.json file in the directory of main_file, or ''.

        Args:
            category (str): Short identifier for the dialog help page
            identifier (str): The second part of the wiki help line on the above page (after the '|').

        Returns:
            See description.
        """
        filename = HelpFinder._json_filename(category)
        if os.path.isfile(filename):
            with open(filename, 'rb') as file:
                contents = orjson.loads(file.read())
                return contents.get(f'{identifier}', '')
        return ''

    @staticmethod
    def _write_to_json(category, urls):
        """Writes the help to json.

        Args:
            category (str): Short identifier for the dialog help page
            urls (dict): Mapping of identifiers to URLs parsed from the wiki page
        """
        # Load all known URLs
        filename = HelpFinder._json_filename(category)
        with open(filename, 'wb') as file:
            data = orjson.dumps(urls)
            file.write(data)


def _find_next_link(content, list_start, list_start_external_link, beg_pos=0):
    """Finds the next link in the HTTP text.

    Args:
        content (str): The HTTP source text.
        list_start (str): The string to search for defining the start of a local link
        list_start_external_link (str): The string to search for defining the start of an external link
        beg_pos (int): The index location in the content string to begin the search

    Returns:
        (tuple(bool,int,str)): A tuple defining whether the next link is external and its location and identifier
    """
    identifier = ""
    internal_link_begin = content.find(list_start, beg_pos)
    link_begin = internal_link_begin
    external_link = False
    id_begin = 0
    if internal_link_begin >= 0:
        id_begin, identifier = _get_identifier(content, internal_link_begin)
    if internal_link_begin < 0 or not identifier:
        external_link_begin = content.find(list_start_external_link, beg_pos)
        if external_link_begin >= 0:
            link_begin = external_link_begin
            id_begin, identifier = _get_identifier(content, external_link_begin)
            if identifier:
                external_link = True
    # Handle case where no identifier is defined
    if (internal_link_begin >= 0 or external_link_begin >= 0) and not identifier and id_begin > 0:
        identifier = 'THIS_LINK_IS_UNUSED'
    return external_link, link_begin, identifier


def _get_identifier(content, link_begin):
    """Gets the link identifier from the entire source HTML and the beginning location of the link."""
    identifier = ""
    link_end = content.find('</li>', link_begin)
    id_begin = content.rfind('|', link_begin, link_end)
    if id_begin >= 0:
        id_begin += 1
        identifier = content[id_begin:link_end].strip()
    return id_begin, identifier
