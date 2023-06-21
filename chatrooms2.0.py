import websockets;
import asyncio;
import json;
import threading;
import requests;
import os;
import re;
import time;
import logging;
import sys;
import datetime;
import random;
import math;
from datetime import datetime;
from websockets import client;
from multiprocessing import Process, Queue;
from firebase import firebase;
print("starting..");
#logging.basicConfig(level = logging.ERROR, filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s');

prefix = ">>";
discKey = os.environ.get('global_key'); 
#discKey = ""; 
discKey = "";
fullEndpoint = 'https://discord.com/api/v10';
fr = firebase.FirebaseApplication("https://gccchat-bf4b2-default-rtdb.firebaseio.com/", None);
channels = 0;
connectionArr = {};
msgCache = [];
commands = [];
karmaCache = {};
karmaThreads = {};
karmaMultiplier = 1;

# -- create random strings --
def genKey(length):
    a = "abcdefghijklmnopqrstuvwxyz";
    oup = '';
    for x in range(length):
        rand = random.randrange(26)
        oup += a[rand]
    return oup;

# -- input sanitation --
def noMentions(s) : #fun regex
    try : 
        i = re.search("<@.{18}>", s); #find raw mention tag
        
        while i: #loop if there is at least one mention tag
            start = int(s[i.start()+2:i.start()+20]); #id of latest user mentioned within string
            realuser = getUser(discKey,start) #get user
            user = "@." + realuser['username']; #get username
            s = re.sub("<@.{18}>", user, s, 1); #replace latest mention tag with new tag
            i = re.search("<@.{18}>", s); #find if there is another mention within 
        i = re.search("<@.{19}>", s); #find raw mention tag
        
        while i: #loop if there is at least one mention tag
            start = int(s[i.start()+2:i.start()+21]); #id of latest user mentioned within string
            realuser = getUser(discKey,start) #get user
            user = "@." + realuser['username']; #get username
            s = re.sub("<@.{19}>", user, s, 1); #replace latest mention tag with new tag
            i = re.search("<@.{19}>", s); #find if there is another mention within 
            
        while re.search("@everyone", s) or re.search("@here", s):
            s = re.sub("@everyone", "@.everyone", s, 1)
            s = re.sub("@here", "@.here", s, 1)
        return s; #final product
    except Exception as e: logging.error("uh oh",exc_info=True);
    
# -- get discord channel--
def getChannel(token,channelID) :
    while True:
        headers = {
            'Authorization' : "Bot " + token
        }
        r = requests.get(fullEndpoint + f'/channels/{channelID}', headers = headers);
        if ('id' in r.json()) : return r.json();
        elif ('code' in r.json() and int(r.json()['code']) == 31008) : time.sleep(int(r.json()['reply-after']));
        else : return None;

# -- get normal user --
def getUser(token,uid) :
    while True:
        headers = {
            'Authorization' : "Bot " + token
        }
        r = requests.get(fullEndpoint + f'/users/{uid}', headers = headers);
        if ('id' in r.json()) : return r.json();
        elif ('code' in r.json() and int(r.json()['code']) == 31008) : time.sleep(int(r.json()['reply-after']));
        else : return None;

# -- get normal guild --
def getGuild(token,guildID):
    while True:
        headers = {
            'Authorization' : "Bot " + token
        }
        r = requests.get(fullEndpoint + f'/guilds/{guildID}', headers = headers);
        if ('id' in r.json()) : return r.json();
        elif ('code' in r.json() and int(r.json()['code']) == 31008) : time.sleep(int(r.json()['reply-after']));
        else : return None;

# -- get guild user (for roles) --
def getGuildUser(token,guildID,uid):
    while True:
        headers = {
            'Authorization' : "Bot " + token
        }
        r = requests.get(fullEndpoint + f'/guilds/{guildID}/members/{uid}', headers = headers);
        if ('user' in r.json()) : return r.json();
        elif ('code' in r.json() and int(r.json()['code']) == 31008) : time.sleep(int(r.json()['reply-after']));
        else : return None;

# -- get all members of a guild --
def getGuildUsers(token,guildID):
    while True:
        headers = {
            'Authorization' : "Bot " + token
        }
        r = requests.get(fullEndpoint + f'/guilds/{guildID}/members?limit=1000', headers = headers);
        fullList = r.json();
        if (str(type(fullList)) == "<class 'list'>") : 
            highestMember = fullList[len(fullList)-1]['user']['id']
            r = requests.get(fullEndpoint + f'/guilds/{guildID}/members?limit=1000&after={highestMember}', headers = headers);
            newList = r.json();
            fullList = fullList + newList;
            while (len(newList) > 0) :
                highestMember = fullList[len(fullList)-1]['user']['id']
                r = requests.get(fullEndpoint + f'/guilds/{guildID}/members?limit=1000&after={highestMember}', headers = headers);
                newList = r.json();
                fullList = fullList + newList;
            
            return fullList;
        elif ('code' in r.json() and int(r.json()['code']) == 31008) : time.sleep(int(r.json()['reply-after']));
        else : return None;
 
#-- get all channels of a guild -- 
def getGuildChannels(token,guildID):
    while True:
        headers = {
            'Authorization' : "Bot " + token
        }
        r = requests.get(fullEndpoint + f'/guilds/{guildID}/channels', headers = headers);
        if (type(r.json()) == list) : return r.json();
        elif ('code' in r.json() and int(r.json()['code']) == 31008) : time.sleep(int(r.json()['reply-after']));
        else : return None;
    
# -- get role permissions --
def getPermissions(token,roleID,guildID):
    while True:
        headers = {
            'Authorization' : "Bot " + token
        }
        r = requests.get(fullEndpoint + f'/guilds/{guildID}/roles', headers = headers);
        roles = r.json();
        if (str(type(roles)) == "<class 'list'>") : 
            for role in roles:
                if (role['id'] == roleID): return role['permissions'];
        elif ('code' in r.json() and int(r.json()['code']) == 31008) : time.sleep(int(r.json()['reply-after']));
        else : return None;

# -- is admin of server --
def isAdmin(c):
    channel = getChannel(discKey,c['channel_id'])
    guildUser = getGuildUser(discKey,channel['guild_id'],c['author']['id']);
    permissions = 0;
    if (len(guildUser['roles']) > 0) : permissions = getPermissions(discKey,guildUser['roles'][0],channel['guild_id']);
    guild = getGuild(discKey,channel['guild_id']);
    return ((int(permissions)) & 0x10 == 0x10 or int(c['author']['id']) == 457231298289860609 or c['author']['id'] == guild['owner_id']);

# -- get discord message --
def getMessage(token,channelID,messageID):
    while True:
        headers = {
            'Authorization' : "Bot " + token
        }
        r = requests.get(fullEndpoint + f'/channels/{channelID}/messages/{messageID}', headers = headers);
        if ('id' in r.json()) : return r.json();
        elif ('code' in r.json() and int(r.json()['code']) == 31008) : time.sleep(int(r.json()['reply-after']));
        else : return None;

# -- fetch specific message within the message cache --
def getChatMessage(message) :
    if (message == None) : return None;
    if (int(message['author']['id']) not in [664307580855648276, 718373371569504337]) :
        for msg in msgCache:
            if (msg['originalMessage']['id'] == message['id']):
                return msg;
    else :
        i  = re.search("#\d\d\d\d",message['content']);
        try : target = message['content'][2:i.start() + 5];
        except : 
            i = re.findall("@.+:\*\*",message['content']);
            try : target = i[0][:len(i[0]) - 3]
            except : return None;
        for msg in msgCache:
            if (target in [f"{msg['originalMessage']['author']['username']}#{msg['originalMessage']['author']['discriminator']}", f"@{msg['originalMessage']['author']['username']}" ]):
                for cachedMsg in msg['msgArr']:
                    if (cachedMsg != None and cachedMsg['id'] == message['id']):
                        return msg;
    return None;

# -- send message within chatroom --
def sendChatMessage(token,m,reference,system = False,announcement = False,room = "all") :
    if (not system) :
        #-- init --
        origin = connectionArr[m['channel_id']]['Destination'];
        message = noMentions(m['content']);
        
        for attachment in m['attachments']:
            message += " " + str(attachment['url']) + " ";
            
        msg = {
            'originalMessage' : m,
            'reactions' : {},
            'msgArr' : []
        }
        
        #-- send message --
        if (str(m['author']['discriminator']) == "0") : u = f"{m['author']['global_name']}@{m['author']['username']}";
        else                                          : u = f"{m['author']['username']}#{m['author']['discriminator']}";
        threadArr = [];
        if (reference) :
            f = open("referenceLog.txt","w");
            f.write(json.dumps(reference));
            chatMessage = getChatMessage(reference);
            f = open("chatMessageLog.txt","w");
            f.write(json.dumps(chatMessage));
            if (chatMessage):
                original = chatMessage['originalMessage'];
                blocked = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{original['channel_id']}/blockedUsers",m['author']['id']);
                if (not blocked) :
                    following = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{original['channel_id']}","following");
                    for blocklist in following :
                        blocked = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{blocklist}/blockedUsers",m['author']['id']);
                        if (blocked) : break;
                if (original['channel_id'] != m['channel_id'] and not blocked) :
                    a = sendMsg(discKey,chatMessage['originalMessage']['channel_id'],f"**{u}:** {message}",original['id'])
                    msg['msgArr'].append(a[1]);
                for ms in chatMessage['msgArr'] :
                    def setInThread(ms):
                        blocked = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{ms['channel_id']}/blockedUsers",m['author']['id']);
                        if (not blocked) :
                            following = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{ms['channel_id']}","following");
                            for blocklist in following :
                                blocked = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{blocklist}/blockedUsers",m['author']['id']);
                                if (blocked) : break;
                        if (ms['channel_id'] != m['channel_id'] and not blocked) :
                            a = sendMsg(discKey,ms['channel_id'],f"**{u}:** {message}",ms['id'])
                            msg['msgArr'].append(a[1]);
                    t = threading.Thread(target = setInThread, args = (ms,));
                    t.start();
                    threadArr.append(t);
            else : sendMsg(discKey,m['channel_id'],"**System:** Message not in message cache",m['id']);
        else :
            for x in connectionArr:
                def setInThread(channel):
                    blocked = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{channel}/blockedUsers",m['author']['id']);
                    if (not blocked) :
                        following = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{channel}","following");
                        for blocklist in following :
                            blocked = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{blocklist}/blockedUsers",m['author']['id']);
                            if (blocked) : break;
                    if (blocked == None):
                        if (connectionArr[channel]['Destination'] == origin and channel != str(m['channel_id']) and channel != "P") :
                            a = sendMsg(discKey,channel,f"**{u}:** {message}",reference);
                            msg['msgArr'].append(a[1]);
                t = threading.Thread(target = setInThread, args = (x,));
                t.start();
                threadArr.append(t);     
        msgCache.append(msg);
        if (len(msgCache) > 5000) :
            msgCache.pop(0);
            
        for thread in threadArr:
            thread.join();
            
        #-- karma --
        def multiplyKarma() :
            global karmaMultiplier;
            karmaMultiplier += 1;
            time.sleep(60);
            karmaMultiplier -= 1;
        if (m['author']['id'] in karmaCache) : 
            usr = karmaCache[m['author']['id']];
            if (usr['eligable']) : 
                if (usr['last'] == False) :
                    for x in karmaCache:
                        karmaCache[x]['last'] = False;
                    usr['last'] = True;
                    threading.Thread(target = multiplyKarma).start();
                karmaCache[m['author']['id']]['karma'] += karmaMultiplier / 10 * (((len(msg['msgArr']) + 1) / 10) + 1);
        else : 
            for x in karmaCache:
                karmaCache[x]['last'] = False;
            karmaCache[m['author']['id']] = { 
                'karma' : karmaMultiplier / 10 * ((len(msg['msgArr']) + 1) / 10 + 1),
                'last'  : True
            };
            threading.Thread(target = multiplyKarma).start();
        karmaCache[m['author']['id']]['eligable'] = False;
        key = genKey(7);
        def setEligable(i,k) :
            time.sleep(2);
            if (any(x != k and karmaThreads[x] == i for x in karmaThreads) == False) : 
                karmaCache[i]['eligable'] = True;
            karmaThreads.pop(k);
        karmaThreads[key] = m['author']['id'];
        threading.Thread(target = setEligable, args = (m['author']['id'],key,)).start();
        
        f = open("karmaCache.txt","w");
        f.write(json.dumps(karmaCache));
        f.close();
        
    else :
        if (announcement):
            for c in connectionArr:
                if (c != "P") : threading.Thread(target = sendEmb, args = (discKey,c,m,)).start();
        else:
            for c in connectionArr:
                if (c != "P" and (connectionArr[c]['Destination'].lower() == room.lower() or room == "all")) : threading.Thread(target = sendMsg, args = (discKey,c,m,False,)).start();

# -- send message --
def sendMsg(token, channelID, message, reference): 
    data = {
        "content" : message,
        "tts" : False
    }
    if (reference) : data['message_reference'] = { "message_id" : reference };
    headers = {
        'Authorization' : "Bot " + token
    }
    if (False) : pass;    
    else :  
        while True:
            r = requests.post(fullEndpoint + f'/channels/{channelID}/messages', headers = headers, json = data);
            if ('id' in r.json()) : return (False, r.json());
            elif ('code' in r.json() and int(r.json()['code']) == 31008) : 
                print("too much!!");
                time.sleep(int(r.json()['reply-after']));
            else : return (True, None, r.json());

# -- send embed --
def sendEmb(token, channelID, embed, reference = None):
    while True:
        data = {
            "tts": False,
            "embeds": [embed]
        }
        if (reference) : data['message_reference'] = { "message_id" : reference };
        headers = {
            'Authorization' : "Bot " + token
        }
        r = requests.post(fullEndpoint + f'/channels/{channelID}/messages', headers = headers, json = data);
        if ('id' in r.json()) : return (False, r.json());
        elif ('code' in r.json() and int(r.json()['code']) == 31008) : time.sleep(int(r.json()['reply-after']));
        else : return (True, None, r.json());

# -- edit message --
def editMsg(token, channelID, message, msgData): 
    for attachment in msgData['attachments']:
        message += " " + str(attachment['url']) + " ";
    msgData["content"] = message;
    headers = {
        'Authorization' : "Bot " + token
    } 
    while True:
        r = requests.patch(fullEndpoint + f'/channels/{channelID}/messages/{msgData["id"]}', headers = headers, json = msgData);
        if ('id' in r.json()) : return (False, r.json());
        elif ('code' in r.json() and int(r.json()['code']) == 31008) : time.sleep(int(r.json()['reply-after']));
        else : return (True, None, r.json());

# -- creates a message string with the appropriate reaction list appended --
def applyReactions(chatMsg) :
    
    totalReactions = 0;
    for r in chatMsg['reactions'] : totalReactions += chatMsg['reactions'][r];
    
    newReactions = "\n`Reactions:";
    for emoji in chatMsg['reactions'] : 
        if (chatMsg['reactions'][emoji] > 0) : newReactions += f" {emoji} {chatMsg['reactions'][emoji]},"
    newReactions = newReactions[:len(newReactions) - 1] + "`";
    
    blank = chatMsg['originalMessage']['content'];
    if (totalReactions == 0) : return blank;
    i = re.findall("`Reactions:.+`",  chatMsg['originalMessage']['content']);
    try : blank = blank[:len(s) - len( i[len(i) - 1])];
    except : pass; 
    
    oup = blank + newReactions;
    
    return oup; 

# -- edit chat message --
def editChatMsg(token, m, con) :
    if (int(m['author']['id']) in [718373371569504337, 664307580855648276]) : return None;
    if (str(m['channel_id']) not in connectionArr) : return None;
    con = noMentions(con);
    chatMsg = getChatMessage(m);
    if (chatMsg == None) : return None;
    threadArr = [];
    if (str(m['author']['discriminator']) == "0") : u = f"**{m['author']['global_name']}@{m['author']['username']}:** ";
    else                                          : u = f"**{m['author']['username']}#{m['author']['discriminator']}:** ";
    con = applyReactions(con);
    for msg in chatMsg['msgArr'] :
        t = threading.Thread(target = editMsg, args = (discKey, msg['channel_id'], u + con, msg,));
        t.start();
        threadArr.append(t);
    for thread in threadArr:
        thread.join();
    return None;
    
# -- add reactions to a chat -- 
def addChatReaction(token, data) :
    def setInThread() :
        
        reactedEmoji = data['emoji'];
        if ("available" in reactedEmoji and not reactedEmoji['available']) : return None;
        emojiString = reactedEmoji['name'];
        if ("require_colons" in reactedEmoji and reactedEmoji['require_colons']) : emojiString = f":{reactedEmoji['name']}:";
    
        message = getMessage(token, data['channel_id'], data['message_id']);
        chatMessage = getChatMessage(message);
        if (chatMessage == None) : return None;
        
        if (emojiString in chatMessage['reactions']) : chatMessage['reactions'][emojiString] += 1;
        else                                         : chatMessage['reactions'][emojiString] = 1;
        
        m = chatMessage['originalMessage']['author'];
        if (str(m['discriminator']) == "0") : u = f"**{m['global_name']}@{m['username']}:** ";
        else                                : u = f"**{m['username']}#{m['discriminator']}:** ";
        con = applyReactions(chatMessage);
        
        threadArr = [];
        for msg in chatMessage['msgArr'] :
            t = threading.Thread(target = editMsg, args = (discKey, msg['channel_id'], u + con, msg,));
            t.start();
            threadArr.append(t);
        for thread in threadArr:
            thread.join();
        
        
    threading.Thread(target = setInThread).start();
  
# -- add reactions to a chat -- 
def remChatReaction(token, data) :
    def setInThread() :
        
        reactedEmoji = data['emoji'];
        if ("available" in reactedEmoji and not reactedEmoji['available']) : return None;
        emojiString = reactedEmoji['name'];
        if ("require_colons" in reactedEmoji and reactedEmoji['require_colons']) : emojiString = f":{reactedEmoji['name']}:";
    
        message = getMessage(token, data['channel_id'], data['message_id']);
        chatMessage = getChatMessage(message);
        if (chatMessage == None) : return None;
        
        chatMessage['reactions'][emojiString] -= 1;
        
        m = chatMessage['originalMessage']['author'];
        if (str(m['discriminator']) == "0") : u = f"**{m['global_name']}@{m['username']}:** ";
        else                                : u = f"**{m['username']}#{m['discriminator']}:** ";
        con = applyReactions(chatMessage);
        
        threadArr = [];
        for msg in chatMessage['msgArr'] :
            t = threading.Thread(target = editMsg, args = (discKey, msg['channel_id'], u + con, msg,));
            t.start();
            threadArr.append(t);
        for thread in threadArr:
            thread.join();
        
        
    threading.Thread(target = setInThread).start();
  
class Events :
    def __init__(this,key):
        
        this.key = key;
        
        this.KEEPALIVE = None;
        this.tempLoop = None;
    
        this.onReady = None;
        this.onConnection = None;
        this.heartbeatAck = None;
        this.onHeartbeat = None;
        this.sendPayload = None;
        this.onMessage = None;
        
        this.gatewayUrl = None;
        this.heartbeatInterval = None;
        this.eventThread = None;
        this.heartbeatThread = None;
        this.session_id = None;
        this.resume_gateway_url = None;
        this.guilds = None;
        this.user = None;  
        
        this.initialize = True;
        this.channels = 0;
        this.karmaLeaderboard = "";
        this.notBlockedMultiplier = 1;
    
    async def updatePresence(this,text) :
        p = {
            "op": 3,
            "d": {
                "since": 91879201,
                "activities": [{
                    "name": text,
                    "type": 2
                }],
                "status": "online",
                "afk": False
                }
            }
        await this.KEEPALIVE.send(json.dumps(p));
        data = await this.KEEPALIVE.recv();
        return json.loads(data);
        
    def connect(this) :
        def initTasks(func) :
            this.tempLoop = asyncio.new_event_loop();
            asyncio.set_event_loop(this.tempLoop);
            this.tempLoop.create_task(func());
            this.tempLoop.run_forever();
        def heartbeatTasks(func) :
            this.heartbeatLoop = asyncio.new_event_loop();
            asyncio.set_event_loop(this.heartbeatLoop);
            
            this.heartbeatLoop.run_until_complete(func());
            this.heartbeatLoop.close();
        def reconnectTask() : 
            print("Reconnecting..");
            this.eventThread = threading.Thread(target = initTasks, args = (setInThread,)).start(); 

        async def startHeartbeat():
            while True:
                try :
                    time.sleep(30);
                    this.tempLoop.create_task(this.KEEPALIVE.send('{"op":1,"d":' + str(this.heartbeatInterval) + '}'));
                except Exception as e:
                    #logging.error("uh oh",exc_info=True);
                    break;
        
        async def setInThread() :
            
            #-- hello exchange --
            this.KEEPALIVE = await websockets.client.connect("wss://gateway.discord.gg/?v=10&encoding=json",ping_timeout = None,close_timeout = None);
            this.heartbeatThread = threading.Thread(target = heartbeatTasks, args = (startHeartbeat,)).start();
            data = await this.KEEPALIVE.recv();
            data = json.loads(data);
            
            if (data["op"] == 10) :
                print("connection made");
                if (str(type(this.onConnection)) == "<class 'function'>") :
                    await this.onConnection();
                    
            this.heartbeatInterval = data['d']['heartbeat_interval'];
            this.gatewayUrl = json.loads(data['d']['_trace'][0])[0];
            
            #-- heartbeat set --
            await this.KEEPALIVE.send('{"op":1,"d":' + str(this.heartbeatInterval) + '}');
            data = await this.KEEPALIVE.recv();
            data = json.loads(data);
            
            if (data['op'] == 11) :
                print("heartbeatAck ready");
                if (str(type(this.heartbeatAck)) == "<class 'function'>") :
                    await this.heartbeatAck();
                
            
            #-- identity exchange --
            identify = {
                          "op": 2,
                          "d": {
                            "token": this.key,
                            "intents": 34307,
                            "properties": {
                              "os": "linux",
                              "browser": "my_library",
                              "device": "my_library"
                            }
                          }
                        }
            
            await this.KEEPALIVE.send(json.dumps(identify));
            data = await this.KEEPALIVE.recv();
            data = json.loads(data);
                                
            #-- if identity exchange success --
            if (data["op"] == 0) :
                if (str(type(this.onReady)) == "<class 'function'>") :
                    await this.onReady(data);
                
                this.initialize = False;    
                this.session_id = data['d']['session_id'];
                this.resume_gateway_url = data['d']['resume_gateway_url'];
                this.user = data['d']['user'];
                this.guilds = data['d']['guilds'];
                
                p = {
                    "op": 3,
                    "d": {
                        "since": 91879201,
                        "activities": [{
                            "name": f"{this.channels} Channels",
                            "type": 2
                        }],
                        "status": "online",
                        "afk": False
                        }
                    }
                await this.KEEPALIVE.send(json.dumps(p));
                data = await this.KEEPALIVE.recv();
                
                while True:
                    try :
                        data = await this.KEEPALIVE.recv();
                        data = json.loads(data);
                        this.sequence = 0;
                        if (data) :
                            if (data['s']) : this.sequence = int(data['s']);
                            if (int(data['op']) == 11) :
                                if (str(type(this.heartbeatAck)) == "<class 'function'>") :
                                    await this.heartbeatAck();
                            elif (int(data['op']) == 0) :
                                if (data['t'] == "MESSAGE_CREATE") :
                                    if (str(type(this.onMessage)) == "<class 'function'>") :
                                        await this.onMessage(data);
                                elif (data['t'] == "MESSAGE_UPDATE") :
                                    try : await editChatMsg(discKey,data['d'],data['d']['content']);
                                    except : pass;
                                elif (data['t'] == "MESSAGE_REACTION_ADD") :
                                    try : await addChatReaction(discKey,data['d']);
                                    except : pass;
                                elif (data['t'] == "MESSAGE_REACTION_REMOVE") :
                                    try : await remChatReaction(discKey,data['d']);
                                    except : pass;
                                
                    except Exception as e:
                        #logging.error("uh oh",exc_info=True);
                        this.restartThread = threading.Thread(target = reconnectTask).start();
                        break;
        this.eventThread = threading.Thread(target = initTasks, args = (setInThread,)).start();

def addCommand(cb):
    p = {
        'cb' : cb,
        'name' : cb.__name__
    }   
    commands.append(p);

async def connect(c,args):
    go = False;
    def setInThread() :
        author = c['author'];
        def limitCB(t) : 
            if (rateLimits[author['id']]['lim'] == 1) :
                threading.Thread(target = sendMsg, args = (discKey, data['channel_id'] ,f"**System:** Please do not spam the connect command! Rate limit for this action 'connect' exceded. Please wait {t} seconds. mrrw~",data['id'],)).start();
        p = applyRateLimit(author['id'], "connect", 60, 2, 60,c);
        if (p == True):
            a = isAdmin(c)
            if (a) : 
                channel = getChannel(discKey,c['channel_id']);
                guild = getGuild(discKey,channel['guild_id']);
                channels = getGuildChannels(discKey,channel['guild_id']);
                room = "global";
                if (len(args) > 0) : room = args[0];
                if (any(connectionArr[x]['Destination'].lower() == room.lower() and x == str(c['channel_id']) for x in connectionArr)):
                    sendMsg(discKey,c['channel_id'],"**System:** You are already connected to this room.",False);
                    return None;
                if (any(x['id'] in connectionArr and connectionArr[x['id']]['Destination'].lower() == room.lower() for x in channels)) :
                    sendMsg(discKey,c['channel_id'],"**System:** You are already have a channel connected to this room.",False);
                    return None;
                else :
                    go = True;
                    postage = {
                        'Destination' : room,
                        'blockedUsers' : {'0' : True},
                        'following' : [0],
                        'followcount' : 0
                    }
                    fr.put("gccchat-bf4b2-default-rtdb/'Channels'",str(c['channel_id']), postage);
                    sendMsg(discKey,c['channel_id'],f"**System:** Connected to room: {room}!",False);
                    sendChatMessage(discKey,f"**System: {guild['name']}** has joined the room **{room}**!",False,True,room = room);
                    postage.pop("blockedUsers");
                    connectionArr[str(c['channel_id'])] = postage;   
            else : sendMsg(discKey,c['channel_id'],"**System:** You do not have permission to use this command",False);
    threading.Thread(target = setInThread).start();
    if (go) :
        events.channels += 1;
        events.updatePresence(f"{events.channels} Channels");
addCommand(connect);

async def disconnect(c,args):
    go = False;
    def setInThread():
        a = isAdmin(c);
        if (a) : 
            channel = getChannel(discKey,c['channel_id']);
            guild = getGuild(discKey,channel['guild_id']);
            if (str(c['channel_id']) in connectionArr):
                go = True;
            
                room = connectionArr[str(c['channel_id'])]['Destination'];
                connectionArr.pop(str(c['channel_id']));
                
                data = fr.get("gccchat-bf4b2-default-rtdb", "'Channels'");
                data.pop(str(c['channel_id']));
                fr.put("gccchat-bf4b2-default-rtdb","'Channels'", data);            

                sendMsg(discKey,c['channel_id'],f"**System:** Disconnected from room: {room}",False);
                sendChatMessage(discKey,f"**System: {guild['name']}** has left the room **{room}**",False,True,room = room);
            else : sendMsg(discKey,c['channel_id'],"**System:** This channel is not connected to a room",False);
        else : sendMsg(discKey,c['channel_id'],"**System:** You do not have permission to use this command",False); 
    threading.Thread(target = setInThread).start();
    if (go) :
        events.channels -= 1;
        events.updatePresence(f"{events.channels} Channels");
addCommand(disconnect);

async def announce(c,args):
    def setInThread():
        if (int(c['author']['id']) == 457231298289860609) :
            if (len(args) == 3) :
                embed = {
                    "title" : args[0],
                    "description" : args[1],
                    "footer" : {
                        "text" : args[2]
                    }
                }
                sendChatMessage(discKey,embed,False,announcement = True, system = True);
            else : sendMsg(discKey,c['channel_id'],"Lol do it right nerd",False);
        else : sendMsg(discKey,c['channel_id'],"ILLEGALE",False);
    threading.Thread(target = setInThread).start();
addCommand(announce);

def blocklist(c,args): 
    def setInThread():
        connection = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{str(c['channel_id'])}","blockedUsers");
        if (connection):
            ls = "";
            count = 0;
            totalCount = 0
            page = 0;
            pagecount = math.ceil(len(connection) / 50)
            try : page = int(args[0]) * 50;
            except : pass;
            for b in connection:
                if (b != "0"):
                    try :
                        if (totalCount >= page) :
                            if (count >= 50) : break;
                            user = getUser(discKey,b);
                            fullUser = f"{user['username']}#{user['discriminator']}"
                            ls += f"**{fullUser}** | *UID: {str(b)}* \n";
                            count += 1;
                        totalCount += 1;
                    except : pass;
            if (len(ls) == 0) : ls = "None"
             
            embed = {
                "title" : "Blocklist for this channel:",
                "description" : ls,
                "footer" : {
                    "text" : f"Page {page + 1} of {pagecount}. mrew~"
                }
            }
             
            sendEmb(discKey,c['channel_id'],embed);
        else : sendMsg(discKey,c['channel_id'],"**System:** You are currently not connected to any rooms and therefore cannot have a blocklist",False);
    threading.Thread(target = setInThread).start();
addCommand(blocklist);

def unblock(c,args) :
    def setInThread():
        blockedUsers = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{str(c['channel_id'])}","blockedUsers");
        a = isAdmin(c);
        if (a):
            if (blockedUsers):
                channel = getChannel(discKey,c['channel_id']);
                guild = getGuild(discKey,channel['guild_id']);
                if (args[0]) :
                    user = getUser(discKey,args[0]);
                    if (user) :
                        if (str(args[0]) in blockedUsers): 
                            blockedUsers.pop(str(user['id']));
                            fr.put(f"gccchat-bf4b2-default-rtdb/'Channels'/{str(c['channel_id'])}","blockedUsers", blockedUsers);
                            sendChatMessage(discKey,f"**System: {guild['name']}** has just unblocked **{user['username']}**! Friendship!",False,system = True,room = connectionArr[c['channel_id']]['Destination']);
                        else : sendMsg(discKey,c['channel_id'],"**System:** Could not find user in blocklist",False);
                    else : sendMsg(discKey,c['channel_id'],"**System:** Could not find user from ID",False);
                else : sendMsg(discKey,c['channel_id'],"**System:** Please specify a user ID to remove from your blocklist",False);  
            else: sendMsg(discKey,c['channel_id'],"**System:** You are currently not connected to any rooms and therefore cannot have people blocked",False);
        else : sendMsg(discKey,c['channel_id'],"**System:** You do not have permission to use this command",False);  
    threading.Thread(target = setInThread).start();
addCommand(unblock);

def leaderboard(c,args) :
    def setInThread() :
        embed = {
            'title' : "Top 10 Users",
            'description' : events.karmaLeaderboard,
            'footer' : {
                'text' : "Leaderboard updates every chat refresh. Mrrw!"
            }
        }
        sendEmb(discKey,c['channel_id'],embed);
    threading.Thread(target = setInThread).start();
addCommand(leaderboard);

def findblocklists(c,args) :
    def setInThread():
        a = isAdmin(c);
        if (a) :
            sendMsg(discKey,c['channel_id'],"**System:** Finding reccomended blocklists..",c['id']);
            channelRank = [];
            currentChannel = fr.get("gccchat-bf4b2-default-rtdb/'Channels'",c['channel_id']);
            if (currentChannel != None) :
                for channel in connectionArr :
                    if (channel != c['channel_id']):
                        data = fr.get("gccchat-bf4b2-default-rtdb/'Channels'",channel);
                        matches = 0;
                        for bUser in currentChannel['blockedUsers'] :
                            if (bUser in data['blockedUsers'] and bUser != True and bUser != "0") : 
                                matches += 1;

                        score = (int(data['followcount']) + 1) * ((matches + 1) / (len(currentChannel['blockedUsers']) + 1));
                        #score is calculated by multiplying the follow count of the comparison channel to the percentage of the ammount of matches found to the total amount of users that are blocked.
                        
                        if (len(channelRank) == 0) : channelRank.append({"c" : data, "score" : score, 'id' : channel, 'match' : matches});
                        else :
                            i = 0;
                            go = True;
                            for element in channelRank: #creates sorted list of all blocklists from highest to lowerst reccomendation score 
                                if (element['score'] <= score) : 
                                    channelRank.insert(i,{"c" : data, "score" : score, 'id' : channel, 'match' : matches});
                                    go = False;
                                    break;
                                i += 1;
                            if (go) : channelRank.insert(i,{"c" : data, "score" : score, 'id' : channel, 'match' : matches}); #if found to be smaller than all elements
                top5 = channelRank[:5];
                sendMsg(discKey,c['channel_id'],top5,False); 
                del channelRank;
                fields = [];
                for channel in top5 :   
                
                    fullChannel = getChannel(discKey,channel['id']);
                    guild = getGuild(discKey,fullChannel['guild_id']);
                    
                    p = {
                        'name' : f"{guild['name']}: {fullChannel['name']}",
                        'value' : f"*ID: {channel['id']}*\n- **Blocklist size:** {len(channel['c']['blockedUsers']) - 1}\n- **Similarity:** Found **{channel['match']}** matching users\n- **Followers:** {channel['c']['followcount']}",
                        'inline' : False
                    }
                    fields.append(p);
                embed = {
                    "title" : "Reccomended Blocklists",
                    "description" : "Here are some blocklists I think you'd like! Its ok, I did the math.. Nya Nya,,",
                    "fields" : fields,
                    "footer" : {
                        "text" : "The algorithm used to find these channels is '(`follow count` + 1) * ((`matching users` + 1) / (`length of your blocklist` + 1))'"
                    }
                }
                sendEmb(discKey,c['channel_id'],embed,reference = c['id']);
                        
            else : sendMsg(discKey,c['channel_id'],"**System:** This channel is not connected to a room",False); 
        else : sendMsg(discKey,c['channel_id'],"**System:** You do not have permission to use this command",False);
    threading.Thread(target = setInThread).start();
addCommand(findblocklists);

def viewchannel(c,args): 
    def setInThread():
        connection = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{str(args[0])}","blockedUsers");
        if (connection):
            ls = "";
            count = 0;
            totalCount = 0
            page = 0;
            pagecount = math.ceil(len(connection) / 50)
            try : page = int(args[1]);
            except : pass;
            for b in connection:
                if (b != "0"):
                    try :
                        if (totalCount >= page) :
                            if (count >= 50) : break;
                            user = getUser(discKey,b);
                            fullUser = f"{user['username']}#{user['discriminator']}"
                            ls += f"**{fullUser}** | *UID: {str(b)}* \n";
                            count += 1;
                        totalCount += 1;
                    except : pass;
            if (len(ls) == 0) : ls = "None"
             
            embed = {
                "title" : f"Blocklist for {args[0]}",
                "description" : ls,
                "footer" : {
                    "text" : f"Page {page + 1} of {pagecount}. mrew~"
                }
            }
             
            sendEmb(discKey,c['channel_id'],embed);
        else : sendMsg(discKey,c['channel_id'],"**System:** Could not find channel",False);
    threading.Thread(target = setInThread).start();
addCommand(viewchannel);

def follow(c,args):
    def setInThread():
        a = isAdmin(c);
        if (a) :
            currentChannel = fr.get("gccchat-bf4b2-default-rtdb/'Channels'",c['channel_id']);
            if (currentChannel) :
                go = False;
                try : 
                    if (args[0]) : go = True;
                except : pass;
                if (go) :
                    targetChannel = fr.get("gccchat-bf4b2-default-rtdb/'Channels'",str(args[0]));
                    if (targetChannel) :
                        if (str(args[0]) not in currentChannel['following']) :
                            currentChannel['following'].append(args[0]);
                            targetChannel['followcount'] += 1;
                            
                            r = fr.put("gccchat-bf4b2-default-rtdb/'Channels'",str(args[0]),targetChannel);
                            r = fr.put("gccchat-bf4b2-default-rtdb/'Channels'",c['channel_id'],currentChannel);
                            
                            fullCurrentChannel = getChannel(discKey,c['channel_id']);
                            fullTargetChannel = getChannel(discKey,str(args[0]));
                            
                            currentGuild = getGuild(discKey,fullCurrentChannel['guild_id']);
                            targetGuild = getGuild(discKey,fullTargetChannel['guild_id']);
                            
                            sendChatMessage(discKey,f"**System: {currentGuild['name']}** has just followed **{targetGuild['name']}: {fullTargetChannel['name']}**! Cooperation!",False,system = True,room = connectionArr[c['channel_id']]['Destination']);
                        else : sendMsg(discKey,c['channel_id'],"**System:** You are already following channel",False);
                    else : sendMsg(discKey,c['channel_id'],"**System:** Cannot find channel from ID",False);  
            else : sendMsg(discKey,c['channel_id'],"**System:** This channel is not connected to a room",False);  
        else : sendMsg(discKey,c['channel_id'],"**System:** You do not have permission to use this command",False);
    threading.Thread(target = setInThread).start();
addCommand(follow);

def unfollow(c,args):
    def setInThread():
        a = isAdmin(c);
        if (a) :
            currentChannel = fr.get("gccchat-bf4b2-default-rtdb/'Channels'",c['channel_id']);
            if (currentChannel) :
                go = False;
                try : 
                    if (args[0]) : go = True;
                except : pass;
                if (go) :
                    targetChannel = fr.get("gccchat-bf4b2-default-rtdb/'Channels'",str(args[0]));
                    if (targetChannel) :
                        if (str(args[0]) in currentChannel['following']) :
                            currentChannel['following'].remove(args[0]);
                            targetChannel['followcount'] -= 1;
                            
                            r = fr.put("gccchat-bf4b2-default-rtdb/'Channels'",str(args[0]),targetChannel);
                            r = fr.put("gccchat-bf4b2-default-rtdb/'Channels'",c['channel_id'],currentChannel);
                            
                            fullCurrentChannel = getChannel(discKey,c['channel_id']);
                            fullTargetChannel = getChannel(discKey,str(args[0]));
                            
                            currentGuild = getGuild(discKey,fullCurrentChannel['guild_id']);
                            targetGuild = getGuild(discKey,fullTargetChannel['guild_id']);
                            
                            sendChatMessage(discKey,f"**System: {currentGuild['name']}** has just unfollowed **{targetGuild['name']}: {fullTargetChannel['name']}**! Dissatisfaction!",False,system = True,room = connectionArr[c['channel_id']]['Destination']);
                        else : sendMsg(discKey,c['channel_id'],"**System:** You are not following this channel",False); 
                    else : sendMsg(discKey,c['channel_id'],"**System:** Cannot find channel from ID",False);  
            else : sendMsg(discKey,c['channel_id'],"**System:** This channel is not connected to a room",False);  
        else : sendMsg(discKey,c['channel_id'],"**System:** You do not have permission to use this command",False);
    threading.Thread(target = setInThread).start();
addCommand(unfollow);

def following(c,args):
    def setInThread():
        connection = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{str(c['channel_id'])}","following");
        if (connection):
            ls = "";
            count = 0;
            totalCount = 0
            page = 0;
            pagecount = math.ceil(len(connection) / 50)
            try : page = int(args[0]) * 50;
            except : pass;
            for b in connection:
                if (b != 0 or b != "0"):
                    if (totalCount >= page) :
                        if (count >= 50) : break;
                        try : 
                            channel = getChannel(discKey,int(b));
                            guild = getGuild(discKey,channel['guild_id']);
                            ls += f"- **{guild['name']} -> {channel['name']}** | *ID: {str(b)}* \n";
                            count += 1;
                        except : pass ;
                    totalCount += 1;
            if (len(ls) == 0) : ls = "None"
             
            embed = {
                "title" : "Follow list:",
                "description" : ls,
                "footer" : {
                    "text" : f"Page {page + 1} of {pagecount}. mrew~"
                }
            }
            sendEmb(discKey,c['channel_id'],embed);
        else : sendMsg(discKey,c['channel_id'],"**System:** You are currently not connected to any rooms and therefore cannot follow any blocklists",False);
    threading.Thread(target = setInThread).start();
addCommand(following);

def help(c,args) :
    def setInThread():
        embed = {
            "title" : "All Commands and Functions:",
            "description" :  "Global chat is a network of various discord channels that all share the same messages with one another. If you send one message in a channel connected to a Chatroom through global chat, it will appear in several different connected channels as well! \n\n\
                              In the help section, anything within '<>' denotes an argument for that command. If an argument is more than one word, surround the argument in double quotation marks for it to work properly. Anything thats prefaced with 'REPLY' means that you need to be replying to a valid Global Chat message for the command to function properly. Happy chatting! Meow~",
            "fields" : [
                {
                    "name" : ">>connect <room>",
                    "value" : "Connects you to the specified room. Leaving `<room>` blank defaults to room 'global'. If the room does not exist, it will automatically create a new one for other people to connect to.",
                    "inline" : False
                },
                {
                    "name" : ">>disconnect",
                    "value" : "Disconnects you from whatever room you're in.",
                    "inline" : False
                },
                {
                    "name" : ">>blocklist <page>",
                    "value" : "Displays list of users that is blocked for the channel. These lists may get large, and can only display 50 users per page. `<page>` specifies the desired page number you wish to view.",
                    "inline" : False
                },
                {
                    "name" : ">>unblock <UID>",
                    "value" : "Unblocks the specified user. `<UID>` must be a valid User ID.",
                    "inline" : False
                },
                {
                    "name" : ">>leaderboard",
                    "value" : "Shows users with the top 10 most social credit.",
                    "inline" : False
                },
                {
                    "name" : ">>findblocklists",
                    "value" : "Displays 5 different channels that Global Chat reccomends you should follow.",
                    "inline" : False
                },
                {
                    "name" : ">>viewchannel <ID> <page>",
                    "value" : "Like `>>blocklist`, except you specify a channel id and page number. Used for viewing another channels blocklists.",
                    "inline" : False
                },
                {
                    "name" : ">>follow <ID>",
                    "value" : "Follows a specified channels blocklist. Following a blocklist means that any users specified in their blocklist will count as valid blocks towards your own channel. This does not override your own blocklist but meerly extends it with another or multiple blocklists.",
                    "inline" : False
                },
                {
                    "name" : ">>unfollow <ID>",
                    "value" : "Unfollows a specified channels blocklist.",
                    "inline" : False
                },
                {
                    "name" : ">>following <page>",
                    "value" : "shows a list of all channels that your channel is following.",
                    "inline" : False
                },
                {
                    "name" : "REPLY >>block",
                    "value" : "Replying to a global chat message with '>>block' will block the person who sent that message in your channel and you will never see their messages again..",
                    "inline" : False
                },
                {
                    "name" : "REPLY >>block -s",
                    "value" : "Replying to a global chat message with '>>block -s' will block everyone in the server the message came from",
                    "inline" : False
                },
                {
                    "name" : "REPLY >>unblock",
                    "value" : "Replying to a global chat message with '>>unblock' will unblock the person who sent the message if they're in your channels blocklist",
                    "inline" : False
                },
                {
                    "name" : "REPLY >>viewuser",
                    "value" : "Replying to a global chat message with '>>viewUser' will display basic information about the user who sent the original message. It will also display stats about the server the message was sent in.",
                    "inline" : False
                },
            ],
            "footer" : {
                "text" : "Global chat is regularly maintained and updated but is also unmoderated. If you see any behavior you deem intolerable, contact one of your server admins or mods so you may block the offender. mew~"
            }
        }   
        sendEmb(discKey,c['channel_id'],embed);
    threading.Thread(target = setInThread).start();
addCommand(help);
 
rateLimits = {};
def applyRateLimit(uid,category,threshold,interval,wait,data) :
    d = datetime.fromisoformat(data['timestamp']);
    
    if (uid not in rateLimits) : 
        rateLimits[uid] = {
            "mute" : False,
            category : [d]
        }
        return True;
    if (category not in rateLimits[uid]) :
        rateLimits[uid][category] = [d];
        return True;
        
    catList = rateLimits[uid][category];
    delta = None;
    catList.append(d);
    if (len(catList) == interval) :
        delta = d - catList[0];
        catList.remove(catList[0]);
    else : return True;
        
    if (delta.total_seconds() < threshold) : 
        rateLimits[uid]['mute'] = True;
        def setInThread() :
            sendMsg(discKey,data['channel_id'],f"**System:** Remember to keep chats clear! You have been rate limited for {wait} seconds.",data['id']);
            time.sleep(wait);
            sendMsg(discKey,data['channel_id'],"**System:** You have been unmuted.",data['id']);
            rateLimits[uid]['mute'] = False;
        threading.Thread(target = setInThread).start();
    
    return not rateLimits[uid]['mute'];
    
def mute(uid,l) :
    rateLimits[uid]['mute'] = True;
    def unmute() :
        time.sleep(l);
        rateLimits[uid]['mute'] = False;
    threading.Thread(target = unmute).start();
    
async def onMsg(data) :
    content = data['content'];
    attachments = data['attachments'];
    author = data['author'];
    if ((content or attachments) and 'bot' not in author) :
            
        if (content not in ['>>block','>>viewUser','>>seeID','>>block -s'] and content[:len(prefix)] == prefix and not data['referenced_message']) :
        
            args = content[len(prefix):]
            newArgs = [];
            newArg = "";
            quoteMode = False;
            for x in args : 
                if (quoteMode) :
                    if (x == '"') : 
                        newArgs.append(newArg);
                        newArg = "";
                        quoteMode = False;
                    else :
                        newArg += x;
                else :
                    if (x == " " and len(newArg) > 0) :
                        newArgs.append(newArg);
                        newArg = "";
                    elif (x == '"'):
                        quoteMode = True;
                    else : 
                        if (x != ' ') : newArg += x;
            if newArg != "" : newArgs.append(newArg)
            args = newArgs
            commandName = args[0];
            args.remove(args[0]);
            
            for command in commands:
                if (command['name'] == commandName) :
                    await command['cb'](data,args);
        else :
            if (any(x == str(data['channel_id']) for x in connectionArr) and 'bot' not in author):
                p = applyRateLimit(author['id'], "globalFaster", 1, 3, 60,data); #for fast messages sent in quick succession 
                if (p == True) : p = applyRateLimit(author['id'], "globalSlower", 5, 4, 30,data); #for messages that might be longer, but might be spammy. (if someone might actually be typing real sentences but still with the intent of spam)
                if (p == True) : p = applyRateLimit(author['id'], "globalSlowest", 7, 6, 10,data); #same deal
                if (p == True) :
                    if (data['referenced_message']) : #replies
                        #-=- reply commands -=-
                        
                        #-- block user --
                        if (content == ">>block") : 
                            def setInThread():
                                a = isAdmin(data)
                                if (a) : 
                                    channel = getChannel(discKey,data['channel_id']);
                                    guild = getGuild(discKey,channel['guild_id']);
                                    msg = getChatMessage(data['referenced_message'])
                                    if (msg):
                                        msg = msg['originalMessage'];
                                        author = msg['author'];
                                        blocked = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{str(data['channel_id'])}/blockedUsers",author['id']);
                                        if (blocked == None) :
                                            if (author['id'] != data['author']['id']) :
                                            
                                                fr.put(f"gccchat-bf4b2-default-rtdb/'Channels'/{str(data['channel_id'])}/blockedUsers",author['id'], True);
                                                sendChatMessage(discKey,f"**System: {guild['name']}** has just blocked **{author['username']}**! Sad!",False,system = True,room = connectionArr[data['channel_id']]['Destination']);
                                                
                                            else : sendMsg(discKey,data['channel_id'],"**System:** You cannot block yourself",False);
                                        else : sendMsg(discKey,data['channel_id'],"**System:** User is already blocked",False);
                                    else : sendMsg(discKey,data['channel_id'],"**System:** Message not in message cache",False);
                                else : sendMsg(discKey,data['channel_id'],"**System:** You do not have permission to use this command",False);
                            threading.Thread(target = setInThread).start();
                         
                        #-- block server -- 
                        elif (content == ">>block -s") :
                            def setInThread() :
                                a = isAdmin(data)
                                if (a) :
                                    channel = getChannel(discKey,data['channel_id']);
                                    guild = getGuild(discKey,channel['guild_id']);
                                    msg = getChatMessage(data['referenced_message'])
                                    if (msg) : 
                                        msg = msg['originalMessage'];
                                        
                                        blockedChannel =  getChannel(discKey,msg['channel_id']);
                                        blockedGuild = getGuild(discKey,blockedChannel['guild_id']);
                                        KILL = getGuildUsers(discKey,blockedGuild['id']);
                                        
                                        killCount = 0;
                                        for dead in KILL:
                                            killCount += 1;
                                            fr.put(f"gccchat-bf4b2-default-rtdb/'Channels'/{str(data['channel_id'])}/blockedUsers",dead['user']['id'], True);
                                        sendChatMessage(discKey,f"**System: {guild['name']}** has just blocked all of **{blockedGuild['name']}**, totalling all {killCount} users! Very Sad!",False,system = True,room = connectionArr[data['channel_id']]['Destination']);
                                        
                                    else : sendMsg(discKey,data['channel_id'],"**System:** Message not in message cache",False);
                                else : sendMsg(discKey,data['channel_id'],"**System:** You do not have permission to use this command",False);
                            threading.Thread(target = setInThread).start();
                        
                        #-- unblock user --
                        elif (content == ">>unblock") :
                            def setInThread():
                                a = isAdmin(data)
                                if (a) :
                                    channel = getChannel(discKey,data['channel_id']);
                                    guild = getGuild(discKey,channel['guild_id']);
                                    msg = getChatMessage(data['referenced_message'])
                                    if (msg) :
                                        msg = msg['originalMessage'];
                                        author = msg['author'];
                                        blockedUsers = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{str(data['channel_id'])}","blockedUsers");
                                        if (author['id'] in blockedUsers) :
                                            blockedUsers.pop(str(author['id']));
                                            fr.put(f"gccchat-bf4b2-default-rtdb/'Channels'/{str(data['channel_id'])}","blockedUsers", blockedUsers);
                                            sendChatMessage(discKey,f"**System: {guild['name']}** has just unblocked **{author['username']}**! Friendship!",False,system = True,room = connectionArr[data['channel_id']]['Destination']);
                                        else : sendMsg(discKey,data['channel_id'],"**System:** Could not find user in blocklist",False);
                                    else : sendMsg(discKey,data['channel_id'],"**System:** Message not in message cache",False);
                                else : sendMsg(discKey,data['channel_id'],"**System:** You do not have permission to use this command",False);
                            threading.Thread(target = setInThread).start();
                        
                        #-- view user --
                        elif (content == ">>viewuser") : 
                            def setInThread():
                                msg = getChatMessage(data['referenced_message'])
                                if (msg):
                                    msg = msg['originalMessage'];
                                    
                                    author = msg['author'];
                                    
                                    blockedAmm = [];
                                    otherUsers = [];
                                    
                                    guild =  getGuild(discKey,msg['guild_id']);
                                    oGuild = getGuild(discKey,data['guild_id']);
                                    guildMembers = getGuildUsers(discKey,msg['guild_id']);
                                    guildUser = getGuildUser(discKey,msg['guild_id'],author['id']);
                                    
                                    seenMembers = [];
                                    
                                    for con in connectionArr:
                                        def t1() :
                                            bar = fr.get(f"gccchat-bf4b2-default-rtdb/'Channels'/{con}","blockedUsers");
                                            if (author['id'] in bar):
                                                blockedAmm.append("");
                                            for user in bar:
                                                if (user not in seenMembers and any(x['user']['id'] == user for x in guildMembers)):
                                                    seenMembers.append(user);  
                                                    otherUsers.append(""); #<-- this is really bad. dont do this. python has forced my hand here
                                        threading.Thread(target = t1).start();
                                                
                                    userNick = author['username'];
                                    userKarma = None;
                                    try : userKarma = round(fr.get("gccchat-bf4b2-default-rtdb/'users'",author['id'])['karma'],2);
                                    except : userKarma = 0; 
                                    if (guildUser['nick'] != None) : userNick = guildUser['nick']
                                    embed = {
                                        'title' : f"Info for {author['username']}",
                                        'fields' : [
                                            {
                                                'name'  : '__User info__',
                                                'value' : f"- Server of origin: **{guild['name']}**\n- Nick in server: **{userNick}**\n- Channels blocking user: **{len(blockedAmm)}**\n- Users social credit score: **{userKarma}**"
                                            },
                                            {
                                                'name'  : f"__{guild['name']} Server Info__",
                                                'value' : f"- Number of users who are blocked in one or more channels: **{len(otherUsers)}**\n- Population: **{len(guildMembers)}**"
                                            }
                                        ],
                                        'thumbnail' : {
                                            'url' : "https://cdn.discordapp.com/avatars/" + author['id'] + "/" + author['avatar']
                                        },
                                        'footer' : {
                                            'text' : "The user who you just viewed has been notified of this action for transparency purposes. Meow,,~"
                                        }
                                    }
                                    sendEmb(discKey,data['channel_id'],embed, reference = data['id']);
                                    sendMsg(discKey,msg['channel_id'],f"**System: {oGuild['name']}** just used the view command on this message!",msg['id']);
                                else : sendMsg(discKey,data['channel_id'],"**System:** Message not in message cache",False);
                            threading.Thread(target = setInThread).start();
                        #-- normal reply --
                        else : sendChatMessage(discKey,data,data['referenced_message']);
                    else:
                        sendChatMessage(discKey,data,False);
   
if __name__ == '__main__':
    events = Events(discKey);
    
    async def createMessageTask(d) :
        await onMsg(d['d']);

    events.onMessage = createMessageTask;
    
    async def onHeartbeat() :
        print(f"heartbeat recieved at {time.localtime()[3]}:{time.localtime()[4]}:{time.localtime()[5]}");
    #events.heartbeatAck = onHeartbeat;
    
    async def onReady(c) :
        if (events.initialize):
            data = fr.get("gccchat-bf4b2-default-rtdb","'Channels'");
            for x in data:
                ch = getChannel(discKey,x);
                if (x != "P" and ch != None):
                    if (any(int(x['id']) == int(ch['guild_id']) for x in c['d']['guilds'])):
                        events.channels+=1;
                        connectionArr[x] = data[x];
                        connectionArr[x].pop("blockedUsers");
                        print(f"Channel {x} connected");
            print(f"Connected '{events.channels}' channels");
            
            print("Dumping karma cache..");
            
            length = 0;
            f = open("karmaCache.txt","r");
            cacheData = {};
            try : cacheData = json.loads(f.read());
            except : pass;
            
            if (cacheData) :
                for user in cacheData:
                    userData = fr.get("gccchat-bf4b2-default-rtdb/'users'",user);
                    if (userData):
                        userData['karma'] += cacheData[user]['karma'];
                        fr.put("gccchat-bf4b2-default-rtdb/'users'",user,userData);
                        length += 1;
                    else : 
                        cacheData[user]['eligable'] = True;
                        fr.put("gccchat-bf4b2-default-rtdb/'users'",user,cacheData[user]);
                        length += 1;
                    print(f"User info for user '{user}' dumped to database");
            f = open("karmaCache.txt","w");
            f.write("");
            f.close();
            
            print(f"Cache dumped! Updated {length} users");
            print("Generating leaderboard..");
            
            userData = fr.get("gccchat-bf4b2-default-rtdb","'users'");
            sortedList = [];
            for user in userData:
                if (sortedList == []) : sortedList.append({"data" : userData[user], "uid" : user});
                else :
                    i = 0;
                    go = True;
                    for element in sortedList:
                        if (userData[user]['karma'] >= element['data']['karma']) :
                            sortedList.insert(i,{"data" : userData[user], "uid" : user});
                            go = False;
                            break;
                        i += 1;
                    if (go ) : sortedList.insert(i,{"data" : userData[user], "uid" : user});
            top10 = sortedList[:10];
            del sortedList;
            i = 1;
            for user in top10 :
                trueUser = getUser(discKey,int(user['uid']));
                events.karmaLeaderboard += f"- **#{i}, {trueUser['username']}#{trueUser['discriminator']}:** {round(user['data']['karma'],2)}\n"
                i += 1;
            print(events.karmaLeaderboard);
            print("Chat now online");
            await events.updatePresence(f"{events.channels} Channels");
            
            length = 0;
            f = open("tipoftheday.json","r");
            tips = json.loads(f.read());
            
            tip = tips['tips'][str(tips['current'])];
            tips['current'] = (tips['current'] + 1) % len(tips['tips']);
            
            f = open("tipoftheday.json","w");
            f.write(json.dumps(tips));
            f.close();
            
            sendChatMessage(discKey,f"**System:** Chat refreshed. Reconnected **{events.channels}** channels. Cleared message cache. Mya!~\n`Tip of the day!: {tip}`",False,system = True);
    events.onReady = onReady;
    events.connect();
