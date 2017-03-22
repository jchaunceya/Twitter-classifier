import re

def removeRT(str):
    if str[:3] == 'RT ':
        return str[3:]
    return str

def makeLower(str):
    return str.lower()

def removeMention(string):
    cleaned =  re.sub('@\w*:?|(\s?https://t.co/\w*)|&amp|(\n)|(&lt;)|(&rt;)|(&gt;)|(%3F)|(,)|(\.+)|(\:)', ' ', string)
    cleaned = re.sub('(\’)', "\'", cleaned)
    cleaned = re.sub('(\")|(\“)|(\!)|(\\?)|(\”)|(\=)(\;)|(\s\-\s)|(\;)|(\')|(https)|(\'s)|(//t)|(#)|(\()|(\))|(\%)', ' ', cleaned)
    cleaned = re.sub('(^\s)|(\:)|(\.)|(…)', '', cleaned)
    cleaned = re.sub('\s+', ' ', cleaned)
    return cleaned
    #re.sub('(@\w*:?\s?)|(\s?https://t.co/\w*)|&amp|(\n)|(&lt;)|(&rt;)|(&gt;)|(%3F)', ' ', string)
    #return re.sub('\s', ',', string)

def commaSeparate(string):
    return re.sub('^\s+', '', string)


def tweet_cleaner(string):
    return commaSeparate(makeLower(removeMention(removeRT(string)))) + '\n'
# to lower
# remove pictures
# remove links
# remove emojis
# remove RT




