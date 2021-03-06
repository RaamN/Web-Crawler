import logging
from datamodel.search.datamodel import ProducedLink, OneUnProcessedGroup, robot_manager
from spacetime_local.IApplication import IApplication
from spacetime_local.declarations import Producer, GetterSetter, Getter
#from lxml import html,etree
from bs4 import BeautifulSoup
import re, os
from time import time

try:
    # For python 2
    from urlparse import urlparse, parse_qs
except ImportError:
    # For python 3
    from urllib.parse import urlparse, parse_qs


logger = logging.getLogger(__name__)
LOG_HEADER = "[CRAWLER]"
url_count = (set() 
    if not os.path.exists("successful_urls.txt") else 
    set([line.strip() for line in open("successful_urls.txt").readlines() if line.strip() != ""]))
MAX_LINKS_TO_DOWNLOAD = 3000
INVALID_LINKS = 0


@Producer(ProducedLink)
@GetterSetter(OneUnProcessedGroup)
class CrawlerFrame(IApplication):

    def __init__(self, frame):
        self.starttime = time()
        # Set app_id <student_id1>_<student_id2>...
        self.app_id = "45618246_33974506"
        # Set user agent string to IR W17 UnderGrad <student_id1>, <student_id2> ...
        # If Graduate studetn, change the UnderGrad part to Grad.
        self.UserAgentString = "IR W17 UnderGrad 45618246, 33974506"
		
        self.frame = frame
        assert(self.UserAgentString != None)
        assert(self.app_id != "")
        if len(url_count) >= MAX_LINKS_TO_DOWNLOAD:
            self.done = True

    def initialize(self):
        self.count = 0
        l = ProducedLink("http://www.ics.uci.edu", self.UserAgentString)
        print l.full_url
        self.frame.add(l)

    def update(self):
        global INVALID_LINKS
        for g in self.frame.get_new(OneUnProcessedGroup):
            print "Got a Group"
            outputLinks, urlResps = process_url_group(g, self.UserAgentString)
            for urlResp in urlResps:
                if urlResp.bad_url and self.UserAgentString not in set(urlResp.dataframe_obj.bad_url):
                    urlResp.dataframe_obj.bad_url += [self.UserAgentString]
            for l in outputLinks:
                if is_valid(l) and robot_manager.Allowed(l, self.UserAgentString):
                    lObj = ProducedLink(l, self.UserAgentString)
                    self.frame.add(lObj)
                else:
                    INVALID_LINKS -= 1
        if len(url_count) >= MAX_LINKS_TO_DOWNLOAD:
            #CALL ANALYTICS
            self.done = True

    def shutdown(self):
        print "downloaded ", len(url_count), " in ", time() - self.starttime, " seconds."
        analytics()
        pass

def save_count(urls):
    global url_count
    urls = set(urls).difference(url_count)
    url_count.update(urls)
    if len(urls):
        with open("successful_urls.txt", "a") as surls:
            surls.write(("\n".join(urls) + "\n").encode("utf-8"))

def analytics():
    totTime, charToStop = 0, 0
    slashCounter = 0
    d = {}
    open_file = open("successful_urls.txt")
    urls = open_file.readlines()
    for i in urls:
        for j in range(len(i)):
            if i[j] == "/":
                slashCounter += 1
                if slashCounter == 3:
                    charToStop = j
        subDomain = i[:charToStop]
        if subDomain in d:
            d[subDomain] += 1
        else:
            d[subDomain] = 1
    with open("analytics.txt", "a") as analysis:
        for i in d:
            analysis.write(i + ": " + str(d[i]) + "\n")
        analysis.write("\nINVALID LINKS: " + str(INVALID_LINKS))
        analysis.write("\n\nPage with the most output links: " + maxPageURL)

def process_url_group(group, useragentstr):
    rawDatas, successfull_urls = group.download(useragentstr, is_valid)
    save_count(successfull_urls)
    return extract_next_links(rawDatas), rawDatas
    
#######################################################################################

maxPageURL = None
maxHref = 0
def extract_next_links(rawDatas):
    outputLinks = list()
    '''
    rawDatas is a list of objs -> [raw_content_obj1, raw_content_obj2, ....]
    Each obj is of type UrlResponse  declared at L28-42 datamodel/search/datamodel.py
    the return of this function should be a list of urls in their absolute form
    Validation of link via is_valid function is done later (see line 42).
    It is not required to remove duplicates that have already been downloaded. 
    The frontier takes care of that.

    Suggested library: lxml
    '''
    global maxPageURL
    global maxHref
    for i in rawDatas:
        sCounter = 0
        charToStop = -1
        hrefCount = 0
        if i.is_redirected:
            if i.http_code >= 400:
                continue
        for j in range(len(i.url)):
            if i.url[j] == "/":
                sCounter += 1
                if sCounter == 3:
                    charToStop = j
                    break
        baseURL = i.url[:charToStop]
        soup = BeautifulSoup(i.content, 'lxml')
        for link in soup.find_all('a'):
            linkToAdd = link.get('href')
            hrefCount += 1
            if linkToAdd == "#" or linkToAdd is None:
                continue
            elif (linkToAdd.startswith("http") != True):
                linkToAdd = baseURL + linkToAdd
            outputLinks.append(linkToAdd)
        if hrefCount > maxHref:
            maxHref = hrefCount
            maxPageURL = i.url
    return outputLinks

def is_valid(url):
    '''
    Function returns True or False based on whether the url has to be downloaded or not.
    Robot rules and duplication rules are checked separately.
    This is a great place to filter out crawler traps.
    
    If "?" is in the URL, it is most likely a dynamic URL, also filter out other common crawler traps
    '''
    global INVALID_LINKS
    if "php" in url or "mailto:" in url or "Mass2Structure" in url or ".db" in url \
            or "archive" in url or ".." in url or "fano" in url or "mlearn" in url or "ganglia" in url or "calendar" in url \
            or "?" in url or "datasets" in url or "~develop" in url or "contact/student-affairs" in url or "cgi" in url:
        INVALID_LINKS += 1
        return False
    list1 = url.split("/")
    if len(list1) != len(set(list1)):
        INVALID_LINKS += 1
        return False
    parsed = urlparse(url)
    if parsed.scheme not in set(["http", "https"]):
        INVALID_LINKS += 1
        return False
    try:
        return ".ics.uci.edu" in parsed.hostname \
            and not re.match(".*\.(css|js|bmp|gif|jpe?g|ico" + "|png|tiff?|mid|mp2|mp3|mp4"\
            + "|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf" \
            + "|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1" \
            + "|thmx|mso|arff|rtf|jar|csv"\
            + "|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
