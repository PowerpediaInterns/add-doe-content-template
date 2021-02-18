# =============================
# IMPORTS
# =============================
import pywikibot    # for making the bot
import requests     # for making requests to the API, in order to generate pages
import re           # for regex methods
import urllib3      # for ignoring the warnings related to making HTTP requests


# =============================
# CONSTANTS: these can be changed by the user as needed
# =============================

# the number of pages this bot will go through before stopping
PAGES_TO_GO_THROUGH = 25

# the title of the page that stores the last page this bot has seen 
# and where to pick up on a later execution
STORAGE_PAGE = "File:AddDOEContentTemplate"

# template name
TEMPLATE_STR = "{{DOE content needed}}"

# regex for detecting DOE headers
title_search = re.compile(r"^(=+)([^=]*)(=+)[ ]?$")
doe_titles = {'topic at doe', 'doe relevance'}



# =============================
# BOT DEFINITION
# =============================

class ContentTemplateBot:
    '''
    A template for other bots. 
    '''

    def __init__(self, site: pywikibot.site.APISite, reference_page_title: str):
        '''
        Creates a new bot.
        The bot will run on the given site. 
        The bot will store its information on the page with the title given. 
        '''
        self.site = site
        self.api_url = site.protocol() + "://" + site.hostname() + site.apipath()
        self.reference_page_title = reference_page_title

    def _get_page_text(self, page_name: str) -> [str]:
        '''
        Gets the text for a page. Returns it as a list of lines.
        '''
        page = pywikibot.Page(self.site, page_name)
        page_lines = page.text.split('\n')
        return page_lines
    
    def pages_from(self, start_point: str) -> "page generator":
        '''
        Returns a generator with pages starting from the given page.
        The number of pages to run on is based on the constant for this module. 
        '''
        # create a new request session 
        my_session = requests.Session()

        # define the necessary restrictions for the search
        api_arguments= {
            "action": "query",
            "format": "json",
            "list": "allpages",
            "apfrom": start_point,
            "aplimit": PAGES_TO_GO_THROUGH
        } 

        # make the request, and store it as a json
        request = my_session.get(url=self.api_url, params=api_arguments, verify=False)
        data = request.json()

        # get and return the received page objects as a generator
        pages = data["query"]["allpages"]
        return pages

    def get_page_start(self) -> str:
        '''
        Returns the page that this bot is supposed to start editing from,
        according to this bot's reference page. 
        '''
        page = pywikibot.Page(self.site, self.reference_page_title)
        return page.text.split('\n')[0]
    
    def set_page_start(self, new_start: str) -> None:
        '''
        Sets the page that this bot will start from next to the string given.
        '''
        page = pywikibot.Page(self.site, self.reference_page_title)
        page.text = new_start
        page.save("Store new page from last execution.")

    def run(self) -> None:
        '''
        Runs the bot on a certain number of pages.
        Records the last page the bot saw on a certain Mediawiki page.
        '''
        # get the pages to run on
        start_page_title = self.get_page_start()
        last_page_seen = ""
        pages_to_run = self.pages_from(start_page_title)

        # loop through pages
        for page in pages_to_run:
            # run main function
            last_page_seen = page['title']
            self.main_function(last_page_seen)
        
        # when done, set the page that we need to start from next
        if len(list(pages_to_run)) < PAGES_TO_GO_THROUGH:
            # if we hit the end, then loop back to beginning
            self.set_page_start("")
        else:
            # otherewise, just record the last page seen
            self.set_page_start(last_page_seen)

    def main_function(self, page_title: str) -> None:
        '''
        Takes a page title. 
        If there is no text under a DOE header, then the bot
        will add the {{DOE content needed}} template.
        '''
        # detect headers
        page_lines = self._get_page_text(page_title)
        lines_to_insert = []

        # keep track of the state of the page
        in_doe_header = False
        this_section_has_content = False

        for line_no, line in enumerate(page_lines):
            if not in_doe_header:
                if self._detect_doe_header(line):
                    # not in doe header, entering doe header
                    in_doe_header = True
                    this_section_has_content = False
            else:
                if self._detect_general_title(line):
                    if not this_section_has_content:
                        # add the template
                        lines_to_insert.append(line_no)

                    if self._detect_doe_header(line):
                        # re-initialize variables for new doe header
                        in_doe_header = True
                        this_section_has_content = False
                else:
                    if len(line.strip()) > 0:
                        # in doe header, encountered content
                        this_section_has_content = True

        # insert templates
        if lines_to_insert:
            templates_inserted = 0
            for line_no in lines_to_insert:
                page_lines.insert(line_no + templates_inserted, TEMPLATE_STR)
                templates_inserted += 1
            
            page = pywikibot.Page(self.site, page_title)
            page.text = '\n'.join(page_lines)
            page.save("Inserted the DOE content needed template.")
        
    def _detect_general_title(self, line: str) -> bool:
        '''
        Returns True if the line is a title.
        Returns False otherwise.
        '''
        # search for title
        m = title_search.search(line)
        return m is not None

    def _detect_doe_header(self, line: str) -> bool: 
        '''
        Finds the title and returns True, or returns False.
        '''
        # search for title
        m = title_search.search(line)

        if m is None:
            return False

        # figure out the level
        start_level = len(m.group(1))
        end_level = len(m.group(3))
        true_level = min(start_level, end_level)

        # parse out the name
        true_name = (m.group(0)[true_level:-true_level]).strip().lower()

        # check name against viable titles
        return true_name in doe_titles
        

# =============================
# SCRIPT
# =============================

if __name__ == "__main__":
    # ignore warning due to making HTTP request (rather than HTTPS)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # create the bot
    bot = ContentTemplateBot(
        site=pywikibot.Site(),
        reference_page_title=STORAGE_PAGE
    )

    # run the bot
    bot.run()
