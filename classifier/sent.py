import statistics
import tweepy
from tweepy import OAuthHandler

import nltk, nltk.tokenize
import queue, threading, math
import sys

import tweetcleaner

import datetime
import MySQLdb
import time



import secrets
access_token = secrets.access_token()
access_token_secret = secrets.access_token_secret()
consumer_key = secrets.consumer_key()
consumer_secret = secrets.consumer_secret()

buffer = queue.Queue()

rtCounter = 0
counters = [0, 0, 0]
rtCounters = [0,0,0]
config = {
    'user': 'db_user',
    'password': 'db_password',
    'host': 'db_host',
    'database': 'db_name',
}

# Each class object recieves all class training tweets, a copy of
# every word that appears in the training data, and its class number.


# 0 = neutral
# 1 = positive
# 2 = negative


# Upon initialization, simple_class_object stores basic information about the training tweets,
# including the number of documents, the number of tokens of each word, and more.
# This is the information that the algorithm references when trying to classify a new tweet.

class Class_Object:
    def __init__(self, class_docs, all_vocab, class_num):
        self._doc_length = []
        self.class_num = class_num
        self.class_docs = class_docs
        self._num_docs = len(class_docs)
        self._class_tokens = []
        for document in class_docs:
            self._class_tokens += nltk.word_tokenize(document)
            self._doc_length.append(len(nltk.word_tokenize(document)))
        self.num_words = len(self._class_tokens)
        self.vocab = set(self._class_tokens)
        self.vocab_length = len(self.vocab)
        self.all_vocab = all_vocab

        self.freq_dist = {}

        for word in self.vocab:
            self.freq_dist[word] = self._class_tokens.count(word)

        self.stddev = statistics.stdev(self._doc_length)
        self.mean = statistics.mean(self._doc_length)

    def return_num_docs(self):
        return self._num_docs

    def return_word_count(self, word):
        if word in self.freq_dist:
            return self.freq_dist[word]
        return 0

    def return_class_tokens(self):
        return self._class_tokens

    def return_product(self, document):
        product = 1
        for word in self.all_vocab:
            numWords = document.count(word)
            # Laplace smoothing just in case the word doesn't occur
            probWord = ((1 + self.return_word_count(word)) / (len(self.all_vocab) + self.num_words))
            probWord = probWord ** numWords
            probWord /= (math.factorial(numWords))
            product *= probWord
        return product * (math.factorial(len(document)))

    # returns the Gaussian probability of the document length

    def return_len_prob(self, length):
        exp = math.e ** (-0.5 * (((length - self.mean) / self.stddev) ** 2))
        denom = math.sqrt(2 * math.pi * (self.stddev ** 2))
        return (exp / denom)


class Classifier:
    def __init__(self, filepath):
        list_docs = [[], [], []]
        alldocs = []
        doclength = []
        totaldocs = 0
        with open(filepath) as documents:
            for line in documents:
                totaldocs += 1
                list_docs[int(line[0])].append(line[2:])
                alldocs += nltk.word_tokenize(line[2:])
                doclength.append(len(nltk.word_tokenize(line[2:])))
        self.num_docs_total = totaldocs
        alldocs = set(alldocs)

        self.neu_obj = class_object(list_docs[0], alldocs, 0)
        self.pos_obj = class_object(list_docs[1], alldocs, 1)
        self.neg_obj = class_object(list_docs[2], alldocs, 2)

        self.std_dev = statistics.stdev(doclength)
        self.all_mean = statistics.mean(doclength)

    def document_len_prob(self, var):  # returns gaussian probability given stddev & mean
        exp = math.e ** (-0.5 * (((var - self.all_mean) / self.std_dev) ** 2))
        denom = math.sqrt(2 * math.pi * (self.std_dev ** 2))
        return (exp / denom)

    def return_doc_prob_class(self, document, class_obj):
        return class_obj.return_product(document) * (class_obj.return_len_prob(len(document)))

    def return_class_frac(self, class_obj):
        return (class_obj.return_num_docs() / self.num_docs_total)

    def return_document_probability(self, document):
        sum = 0

        sum += self.return_doc_prob_class(document, self.neu_obj) * self.return_class_frac(self.neu_obj)
        sum += self.return_doc_prob_class(document, self.pos_obj) * self.return_class_frac(self.pos_obj)
        sum += self.return_doc_prob_class(document, self.neg_obj) * self.return_class_frac(self.neg_obj)

        return sum

    def return_given_doc_prob_class(self, document, class_obj):
        i = class_obj.return_product( document ) * (class_obj.return_len_prob(len(document)))
        i *= class_obj.return_num_docs() / self.num_docs_total
        i /= self.return_document_probability(document)
        return i
        # return (((self.return_doc_prob_class(document, class_obj)) * (self.return_class_frac(class_obj))) / (
        # self.return_document_probability(document)))

    # Trying to avoid conditional branching, in an effort to increase performance 
    # Returns list index - the number representing class

    def make_prediction(self, document):
        document = nltk.word_tokenize(document)
        pred_list = []
        pred_list.append(self.return_given_doc_prob_class(document, self.neu_obj))
        pred_list.append(self.return_given_doc_prob_class(document, self.pos_obj))
        pred_list.append(self.return_given_doc_prob_class(document, self.neg_obj))
        return pred_list.index(max(pred_list))

def read_buff(obj_wrap):
    global buffer
    global rtCounter
    global rtCounters
    global counter

    while buffer.qsize() < 10000:
        # buffer should never have more than 10000 tweets at once.
        # if it does, something is wrong
        try:
            to_write = buffer.get_nowait()
            classnum = obj_wrap.make_prediction(to_write[2:])
            counter += 1
            rtCounter += int(to_write[0])
            counters[classnum] += 1
            rtCounters[classnum] += int(to_write[0])
        except(queue.Empty):
            pass


def write_pred(obj_wrap):

    bufreadOne = threading.Thread(target=read_buff, args=(obj_wrap,))
    bufreadTwo = threading.Thread(target=read_buff, args=(obj_wrap,))
    bufreadThree = threading.Thread(target=read_buff, args=(obj_wrap,))
    bufreadFour = threading.Thread(target=read_buff, args=(obj_wrap,))
    bufreadFive = threading.Thread(target=read_buff, args=(obj_wrap,))
    bufreadSix = threading.Thread(target=read_buff, args=(obj_wrap,))
    bufreadSeven = threading.Thread(target=read_buff, args=(obj_wrap,))
    bufreadEight = threading.Thread(target=read_buff, args=(obj_wrap,))
    
    bufreadOne.start()
    bufreadTwo.start()
    bufreadThree.start()
    bufreadFour.start()
    bufreadFive.start()
    bufreadSix.start()
    bufreadSeven.start()
    bufreadEight.start()

    global counter
    global rtCounters
    global rtCounter
    global counters

    insertob = DBInsertOb()
    now = datetime.datetime.utcnow()
    rtCounter = 0
    counter = 0
    counters = [0,0,0]
    rtCounters = [0, 0, 0]
    global buffer

    while buffer.qsize() < 10000:
        # buffer should never have more than 10000 tweets at once.
        # if it does, something is wrong
        time.sleep(60)

        now = datetime.datetime.utcnow()

        print("buffer size: \t\t" +  str(buffer.qsize()))
        dateobject = DataObject(counters[1], counters[2], counters[0],
                                counter, 
                                rtCounters[1], rtCounters[2], rtCounters[0])

        print("num retweets: \t" + str(rtCounter))
        print("percent retweets:\t" + str((100 * rtCounter)/counter))
        print("negative rt %:\t\t" + str((100 * rtCounters[0])/counters[0]))
        print("positive rt %:\t\t" + str((100 * rtCounters[1])/counters[1]))
        print("neu rt %:\t" + str((100 * rtCounters[2])/counters[2]))
        print("num pos:\t\t" + str(counters[1]))
        print("num neg:\t\t" + str(counters[0]))
        print("num neu:\t\t" + str(counters[2]))

        insertob.insert_into_db(dateobject)
        counters = [0, 0, 0]
        counter = 0
        rtCounter = 0
        rtCounters = [0, 0, 0]
        
    print("buffer exceeded max size")



class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        temp = tweetcleaner.tweet_cleaner(status.text)  # get the cleaned tweet text
        global buffer
        try:
            buffer.put_nowait(str(int(hasattr(status, 'retweeted_status'))) + ',' + temp)  # put text of most recent status into global tweet buffer
        except:
            pass
    def on_error(self, status):
        print("error!! printed on error!! ")
        print(status)

        if status == 420:  # if Twitter rejects connection, close program
            sys.exit()

    def on_disconnect(self, notice):
        print(notice)


class DataObject:
    def __init__(self, pos, neg, neu, neg_rt, pos_rt, neu_rt, total_num):
        self.pos_num = pos
        self.neu_num = neu
        self.neg_num = neg
        self.neg_num_rt = neg_rt
        self.pos_num_rt = pos_rt
        self.neu_num_rt = neu_rt
        self.total_num = total_num
        self.time_of = str(datetime.datetime.utcnow())


class DBInsertOb:
    def __init__(self):
        self.num_entries = 0
        try:
            self.db = MySQLdb.connect(**config)
            self.cursor = self.db.cursor()

            print('connection successful')

        except MySQLdb.MySQLError as err:
            print("Unable to connect: {}".format(err))
            sys.exit()

    def insert_into_db(self, data):
        query = (
        """INSERT INTO sent_datedata(num_pos, num_neg, num_neu, num_all, num_pos_rt, num_neg_rt, num_neu_rt,  date_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""")
        args = (
        data.pos_num, data.neg_num, data.neu_num, data.neg_num_rt, data.pos_num_rt, data.neu_num_rt, data.total_num, data.time_of)

        try:
            self.cursor.execute(query, args)
            self.db.commit()
            print('inserted')
        except mysql.connector.Error as err:
            print("Unable to connect: {}".format(err))
            self.db.close()
            self.cursor.close()
        #print(self.cursor.getlastrowid())


def start_twitter_stream():
    print("stream started")
    while True:
        try:
            stream.filter(track=['trump'], languages=['en'])
        except:
            continue

if __name__ == '__main__':
    l = MyStreamListener()
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    stream = tweepy.Stream(auth, l)
    train_docs = '../data/trump_data_3.txt'

    objlist1 = Classifier(train_docs)

    bufreadOne = threading.Thread(target=write_pred, args=(objlist1,))

    streamThread = threading.Thread(target=start_twitter_stream, args=())

    bufreadOne.start()

    streamThread.start()


