import asyncio
import json
import os
import re
import requests

API_URL = 'https://graphql.anilist.co'

GET_COMMENTS_QUERY = '''
query($page: Int, $userId: Int) {
  Page(page:$page) {
    pageInfo {
      total
      currentPage
      hasNextPage
    }
    threadComments(userId:$userId) {
       threadId
       id
       comment
       thread {
        title
      }
    }
  }
}
'''

GET_THREADS_QUERY = '''
query($page:Int, $userId:Int) {
  Page(page:$page) {
    pageInfo {
      total
      currentPage
      hasNextPage
    }
    threads(userId:$userId) {
      id
      title
      body
    }
  }
}
'''

GET_ACTIVITIES_QUERY = '''
query($page: Int, $userId: Int) {
  Page(page:$page) {
    pageInfo {
      total
      currentPage
      hasNextPage
    }
    activities(userId:$userId, type_in:[TEXT, MESSAGE]) {
      ...on MessageActivity{
        id
        message
      }
      ...on TextActivity{
        id
        text
      }
    }
  }
}
'''

user_ids = [
    207043, 
    131231,
]

def clean_for_windows(text):
    return re.sub(r'(?u)[^-\w.]', '_', text)

def post_query(query, variables):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    response = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
    return response.text

def get_image_links(text):
    expressions = re.findall(r"imgur.com\/\w+.png", text)
    return expressions

def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped

@background
def download_thread_links(user_id, thread, links):
    path = './res/' + str(user_id) + '/threads/' + clean_for_windows(thread['title']) + '/'
    
    if not os.path.exists(path):
        os.makedirs(path)

    for link in links:
        with open(path + link[link.rindex('/') + 1:], 'wb') as f:
            f.write(requests.get('https://' + link).content)

@background
def download_comment_links(user_id, comment, links):
    path = './res/' + str(user_id) + '/comments/' + str(comment['id']) + '/'

    if not os.path.exists(path):
        os.makedirs(path)
        
    for link in links:
        with open(path + link[link.rindex('/') + 1:], 'wb') as f:
            f.write(requests.get('https://' + link).content)

@background
def download_activity_links(user_id, activity, links):
    path = './res/' + str(user_id) + '/activities/' + str(activity['id']) + '/'

    if not os.path.exists(path):
        os.makedirs(path)
        
    for link in links:
        with open(path + link[link.rindex('/') + 1:], 'wb') as f:
            f.write(requests.get('https://' + link).content)

if __name__ == '__main__':
    for user_id in user_ids:
        # Parse threads
        threads_response = json.loads(post_query(GET_THREADS_QUERY, {
            'page': 1,
            'userId': user_id,
        }))

        threads = threads_response['data']['Page']['threads']

        print("Parsing {} threads...".format(threads_response['data']['Page']['pageInfo']['total']))

        while threads_response['data']['Page']['pageInfo']['hasNextPage']:
            threads_response = json.loads(post_query(GET_THREADS_QUERY, {
                'page': threads_response['data']['Page']['pageInfo']['currentPage'] + 1,
                'userId': user_id,
            }))

            threads.extend(threads_response['data']['Page']['threads'])

        for thread in threads:
            links = get_image_links(thread['body'])
            
            if len(links):
                download_thread_links(user_id, thread, links)
        
        # Parse comments
        comments_response = json.loads(post_query(GET_COMMENTS_QUERY, {
            'page': 1,
            'userId': user_id,
        }))

        comments = comments_response['data']['Page']['threadComments']

        print("Parsing {} comments...".format(comments_response['data']['Page']['pageInfo']['total']))

        while comments_response['data']['Page']['pageInfo']['hasNextPage']:
            comments_response = json.loads(post_query(GET_COMMENTS_QUERY, {
                'page': comments_response['data']['Page']['pageInfo']['currentPage'] + 1,
                'userId': user_id,
            }))

            comments.extend(comments_response['data']['Page']['threadComments'])

        for comment in comments:
            links = get_image_links(comment['comment'])

            if len(links):
                download_comment_links(user_id, comment, links)

        # Parse activities
        activities_response = json.loads(post_query(GET_ACTIVITIES_QUERY, {
            'page': 1,
            'userId': user_id,
        }))

        activities = activities_response['data']['Page']['activities']

        print("Parsing {} activities...".format(activities_response['data']['Page']['pageInfo']['total']))

        while activities_response['data']['Page']['pageInfo']['hasNextPage']:
            activities_response = json.loads(post_query(GET_ACTIVITIES_QUERY, {
                'page': activities_response['data']['Page']['pageInfo']['currentPage'] + 1,
                'userId': user_id,
            }))

            activities.extend(activities_response['data']['Page']['activities'])

        for activity in activities:
            links = get_image_links(activity['text'] if 'text' in activity.keys() else activity['message'])

            if len(links):
                download_activity_links(user_id, activity, links)

