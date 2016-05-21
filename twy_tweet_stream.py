'''stream a set of users current tweets into a database'''

# get the Twitter API app Oauth tokens
import sys
TWITDIR = 'U:\Documents\Project\demoapptwitter'
sys.path.insert(0, TWITDIR)
import config

# Thread as the consumer of the Twitter stream will run in a separate thread.
from threading import Thread

# provide a lock-free way to move messages from one thread to another.
from queue import Queue

from twython import TwythonStreamer

# handle certain errors that streaming can generate:
from requests.exceptions import ChunkedEncodingError

import json
import random

# implement our extension to Twythons streamer
class TwitterStream(TwythonStreamer):
    '''Set up a queue for the tweets. Provides information on what to do
     when a tweet is received and on errors.'''
    def __init__(self, consumer_key, consumer_secret, token, token_secret, tqueue):
        self.tweet_queue = tqueue
        # pass credentials to the parent class for authenticating:
        super(TwitterStream, self).__init__(consumer_key, consumer_secret, token, token_secret)

    def on_success(self, data):
        if 'text' in data:
            self.tweet_queue.put(data)

    def on_error(self, status_code, data):
        print(status_code)
        
        # Uncomment to stop trying to get data because of the error
        self.disconnect()


def stream_tweets(tweets_queue):
    ''' samples the stream API and handles errors'''
    # OAuth credentials 
    consumer_key = config.ul_consumer_key
    consumer_secret = config.ul_consumer_secret
    token = config.ul_access_token
    token_secret = config.ul_access_secret
    try:
        stream = TwitterStream(consumer_key, consumer_secret, token, token_secret, tweets_queue)
        # filter on users / keywords
        # stream.statuses.filter(track='flooding', language='en')
        stream.statuses.filter(follow=comma_sep_string)

    except ChunkedEncodingError:
        # Sometimes the API sends back one byte less than expected which results in an exception in the
        # current version of the requests library
        stream_tweets(tweet_queue)


def process_tweets(dbc, tweets_queue):
    '''loop over the queue and process each elementwise'''
    count = 0
    
    while True:
        tweet = tweets_queue.get()
        # 1 million
        if count < 1000000:
            count += 1
        else:
            self.disconnect()
            exit('max no collected:' + count)

        # debug:
        # print(tweet['text'].encode('utf-8'))
        
        # insert tweet dict into mongodb
        dbc.insert_one(tweet)
        tweets_queue.task_done()

def get_dbc(db_name, collection, host):
    '''Convenience wrapper for a collection in mongoDB'''
    from pymongo import MongoClient
    try:
        client = MongoClient(host)
    except e:
        print ("Could not connect to MongoDB: %s" % e)

    db = client[db_name]

    return db[collection]


if __name__ == '__main__':
    ''' run the script, be sure to adjust the query as needed'''

    from twython_search_api_lib import load_tweet_ids
    ids = load_tweet_ids(TWITDIR + r'\results.json', 1000)

    # ...and remove any users we do not wish to search on:
    users = [user for user in ids if user not in config.excluded_users]
    # then draw a random subsample of 50 of these:
    random.shuffle(users)
    users = random.sample(users, 50)

    comma_sep_string = ",".join(users)
    
    # remote db via pymongo
    dbc = get_dbc('database', 'streamedtweets', config.MONGO_URI)
    
    tweet_queue = Queue()
    Thread(target=stream_tweets, args=(tweet_queue,), daemon=True).start()

    process_tweets(dbc, tweet_queue)