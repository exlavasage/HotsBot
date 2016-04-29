import telepot
from telepot.namedtuple import InlineQueryResultArticle
import subprocess
import sys
import os
import time
import re
import requests
from bs4 import BeautifulSoup
from bs4 import UnicodeDammit
import random
from ConfigParser import RawConfigParser

queryResponse = 0
maxMessageSize = 4096
ownerId = 0
to_exit = False

def parse_query(query):
    m = re.match('^/?(?P<command>[^@ ]*)(@teakhotsbot)? ?(?P<args>.*)$', query)
    if m:
        return {'command': m.group('command'), 'args': m.group('args')}
           
    return {}

def handle_table(table):
    results = []
    for row in table.find_all('tr'):
        rr = []
        for td in row.find_all(['td', 'th']):
            if td.string == None:
                rr.append('')
            else:
                rr.append(td.string)
        results.append(rr)
    return results

def is_end(tag):
    return 'p' in tag and len(tag.contents) == 1 and 'img' in tag.contents[0]

def handle_message(msg):    
    flavor = telepot.flavor(msg)
    parse_mode = 'markdown'

    query = ''
    if flavor == 'normal':
        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type == 'text':
            query = msg['text'].lower()            
    elif flavor == 'inline_query':
        query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
        query = query_string.lower()

    query = parse_query(query)    
    if len(query) == 0:
        return

    response = ''
    global ownerId
    if query['command'] == 'redeploy' and int(chat_id) == int(ownerId):
        #subprocess.call(['git', 'pull'])
        subprocess.Popen('cd '+os.getcwd()+' & git pull & C:\Python27\Python.exe HotsBot.py redeploy', shell=True)
        response = 'Redeploying: '
        bot.sendMessage(chat_id, response)
        global to_exit
        to_exit = True
        return
    if query['command'] == 'free':        
        r = requests.get('http://heroesofthestorm.gamepedia.com/Free_rotation')        
        soup = BeautifulSoup(r.content)
        results = []        
        for child in soup.select('div.link'):            
            results.append(child.contents[0]['title'])
    
        response = 'Free rotation: '
        for i in range(0, len(results)):
            if i + 1 < len(results):
                response = response + results[i] + u', '
            else:
                response = response + results[i]        
    elif query['command'] == 'sale':
        r = requests.get('http://us.battle.net/heroes/en/blog/')
        soup = BeautifulSoup(r.content)
        url = soup.select('ul[class=news-list]')[1].select('a[href*=weekly-sale]')[0]['href']        
        r = requests.get('http://us.battle.net/'+url)
        soup = BeautifulSoup(r.content)        
        
        response = ''
        for child in soup.select('p[style^=margin:0]'):
            for part in child.stripped_strings:
                response = response + part
            response = response + u'\n'
    elif query['command'] == 'random':
        r = requests.get('http://heroesofthestorm.gamepedia.com/Hero')        
        soup = BeautifulSoup(r.content)
        results = []
        for child in soup.select('span[id$='+query['args'].capitalize()+'_heroes]'):            
            child = child.parent.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling
            for hero in child.select("div.link"):                
                results.append(hero.contents[0]['title'])
    
        if len(query['args']) > 0:
            response = "Random "+query['args']+" hero is "+results[random.randrange(len(results))]
        else:
            response = "Random hero is "+results[random.randrange(len(results))]
    elif query['command'] == 'patch':
        r = requests.get('http://us.battle.net/heroes/en/blog/')
        soup = BeautifulSoup(r.content, 'html5lib')                
        url = soup.select('ul[class=news-list]')[1].find_next('a', text=re.compile('Notes'))['href']
        url = 'http://us.battle.net' + url
        r = requests.get(url)    
        soup = BeautifulSoup(UnicodeDammit(r.content, is_html=True).unicode_markup, 'html5lib')        
        
        results = []
        if len(query['args']) > 0:
            catagory = soup.find(['h3','h4'], text=query['args'].title())
            if not catagory:
                catagory = soup.find('a', attrs={'name':query['args'].title().replace(' ', '_')}).parent
            end = catagory.find_next(['h3', 'h4'])
            print catagory.find_next('img[alt*=InvisibleDividerLine]')
            hard_end = catagory.find_next('div', 'blockquote')            

            results = []
            pop = False
            for child in catagory.find_next_siblings():
                if child == end:                    
                    break
                if child == hard_end:
                    break

                if child.name == 'table':
                    results.append(handle_table(child))            
                else:                    
                    for part in child.strings:                    
                        results.append(part)        

            while type(results[-1]) != list and results[-1].isspace():
                results.pop()
            if type(results[-1]) != list and 'Return' in results[-1]:     
                results.pop()
                            
            response = query['args'].title()+'\n'
            for result in results:
                if type(result) == list:
                    response = response + '```\n'                    
                    for r in result:
                        row_format ="{:<14}" * len(r)                      
                        response = response + row_format.format(*r) + '\n'
                    response = response + '```'                    
                else:
                    response = response + result                    
        else:
            response = 'Patch Notes:\n'
            if soup.find('ul[class=toc-list]') :
                for child in soup.find('ul[class=toc-list]').select('li'):                    
                    response = response + '['+child.getText()+']('+url+child.select('a[href]')[0]['href']+')\n'
            else:                
                print len(soup.find('article').find_all('h3'))
                for child in soup.find('article').find_all('h3'):
                    response = response + '['+child.getText()+']('+url+'#'+child.getText()+')\n'                
            response = response + 'Use /patch [Section] for more information'    
    if len(response) == 0:
        return    
    
    print query['command'].capitalize() + ' ' + query['args'].title()
    print len(response)        
    if flavor == 'normal':
        global maxMessageSize
        while len(response) > 0:
            length = len(response)        
            rest = ''
            while length > maxMessageSize:
                newline = response.rfind('\n')
                rest = response[newline:] + rest
                response = response[:newline]
                length = len(response)
            bot.sendMessage(chat_id, response, parse_mode=parse_mode)
            response = rest            
    elif flavor == 'inline_query':
        global queryResponse
        response = [InlineQueryResultArticle(id=str(queryResponse), title=response, message_text=response)]
        queryResponse += 1
        bot.answerInlineQuery(query_id, response)
       

parser = RawConfigParser()
parser.read('hots.cfg')
api_key = parser.get('config', 'api_key')
ownerId = parser.get('config', 'owner_id')

bot = telepot.Bot(api_key)
bot.getMe()

if len(sys.argv) > 1 and 'redeploy' in sys.argv[1]:
    time.sleep(10)
    bot.sendMessage(ownerId, 'Restarted: ')
print 'Hello'
bot.notifyOnMessage(handle_message)

while not to_exit:
    time.sleep(1)
time.sleep(1)
print 'Goodbye'
