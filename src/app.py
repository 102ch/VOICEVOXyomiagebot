import discord
from discord import Embed, Interaction, ui
import os
from pathlib import Path
from voicevox_core import VoicevoxCore, METAS
core = VoicevoxCore(open_jtalk_dict_dir=Path("open_jtalk_dic_utf_8-1.11"))
from pprint import pprint
from discord.ext import commands
import asyncio
from collections import defaultdict, deque
import re
import random
import copy
import pickle
import os

metas = str(METAS)
namelist = {}
metalist = []
stylist1 = []
stylist2 = []
stylist3 = []
stylist4 = {}
idlist = {}
fixedlist = []
metaar = ""

#speaker_id = 3

TOKEN = os.environ["DISCORD_TOKEN"]
intents = discord.Intents.all()
client = discord.Client(intents=intents)
queue_dict = defaultdict(deque)
connecting_channels = set()
url = re.compile('^http')
mention = re.compile('<@[^>]*>')
stamp = re.compile('<:([^:]*):.*>')

guild = os.environ["DISCORD_GUILD"]
#guild = 945735786739933275 #自分鯖
channel = os.environ["DISCORD_CHANNEL"]
application_id = os.environ["DISCORD_APPLICATION_ID"]
bot = commands.Bot(
    command_prefix="/",
    intents=discord.Intents.all(),
    application_id=application_id
)
tree = bot.tree

voice = None
volume = None
currentChannel = None

def enqueue(voice_client: discord.VoiceClient, guild: discord.guild, source, filename: str):
    queue = queue_dict[guild.id]
    queue.append([source, filename])
    if not voice_client:
        return
    if not voice_client.is_playing():
        play(voice_client, queue)


def play(voice_client: discord.VoiceClient, queue: deque):
    if not queue or voice_client.is_playing():
        return
    source = queue.popleft()
    # os.remove(source[1])
    voice_client.play(source[0], after=lambda e: play(voice_client, queue))

def replaceStamp(text: str) -> str:
    text = re.sub('<:([^:]*):.*>', '\\1', text)
    return text

async def replaceUserName(text: str) -> str:
    for word in text.split():
        if not mention.match(word):
            continue
        print(word)
        userId = re.sub('<@([^>]*)>', '\\1', word)
        print(userId)
        userName = str(await bot.fetch_user(userId))
        userName = re.sub('#.*', '', userName)
        text = text.replace(word, '@' + userName)
    return text

async def jtalk(t) -> str:
    global speaker_id
    if not core.is_model_loaded(speaker_id):  # モデルが読み込まれていない場合
            core.load_model(speaker_id)  # 指定したidのモデルを読み込む
    wave_bytes = core.tts(t, speaker_id)  # 音声合成を行う
    with open("output.mp3", "wb") as f:
        f.write(wave_bytes)  # ファイルに書き出す
        #client.get_guild(guild).voice_client.play(source)
        #bot.get_guild(guild).voice_client.play(discord.FFmpegPCMAudio("output.mp3"))
    return 'output.mp3'

def get_voice_client(channel_id: int) -> discord.VoiceClient | None:
    for client in bot.voice_clients:
        if client.channel.id == channel_id:
            return client
    else:
        return None

async def user_sep(user_name: str) -> str:
    global namelist 
    if namelist.get(user_name) == None:       
        namelist.setdefault(user_name, random.randint(1, 51))
        with open('school.binaryfile', 'wb') as web:
            pickle.dump(namelist, web)

async def text_check(text: str, user_name: str) -> str:
    #print(text)
    global speaker_id
    if len(text) > 100:
        raise Exception("文字数が長すぎるよ")
    if stamp.search(text):
        text = replaceStamp(text)
    if mention.search(text):
        text = await replaceUserName(text)
    #text = re.sub('#.*', '', str(user_name)) + ' ' + text
    text = re.sub('http.*', '', text)
    match = re.findall(r'[a-zA-Z0-9ぁ-んァ-ン一-龥]', text)
    if match==[]:
        #return await bot.process_commands(text)
        return
    #text = replaceDict(text)
    if len(text) > 100:
        raise Exception("文字数が長すぎるよ")
    await user_sep(user_name)
    speaker_id = namelist[user_name]
    filename = await jtalk(text)
    if os.path.getsize(filename) > 10000000:
        raise Exception("再生時間が長すぎるよ")
    return text, filename

async def listmk():
    global metaar
    for meta in METAS:
        metalist.append(meta.name)
        for style in meta.styles:
            stylist1.append(style.name + "  " + str(style.id))
            stylist4.setdefault(style.id, style.name)
            idlist[style.id] = meta.name + '  ' +style.name
        st = copy.copy(stylist1)
        sts = copy.copy(stylist4)
        stylist2.append(st)
        stylist3.append(sts)
        stylist1.clear()
        stylist4.clear()

@bot.event
async def on_ready():
    global namelist 
    #await client.get_channel(channel).connect()
    await tree.sync()   
    await listmk()
    with open('school.binaryfile', 'rb') as web:
        namelist = pickle.load(web)
    print('connected')

@bot.event
async def on_message(message: discord.Message):
    #if message.author.bot:
    if message.author == client.user:
        return await bot.process_commands(message)
    volume = 0.5
    voice = get_voice_client(message.channel.id)

    if not voice:
        return await bot.process_commands(message)

    if voice is True and volume is None:
        source = discord.PCMVolumeTransformer(voice.source)
        volume = source.volume
    
    text = message.content

    try:
        text, filename = await text_check(text, message.author.name)
    except Exception as e:
        return await bot.process_commands(message) #await message.channel.send(e)

    if not message.guild.voice_client:
        return await bot.process_commands(message)

    enqueue(message.guild.voice_client, message.guild,
            discord.FFmpegPCMAudio(filename), filename)
    # timer = Timer(3, os.remove, (filename, ))
    # timer.start()
    # os.remove(filename)
    # コマンド側へメッセージ内容を渡す
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member: discord.Member, before:discord.VoiceState, after:discord.VoiceState):
    allbot = True
    for mem in before.channel.members:
         if  not mem.bot:
             allbot = False
    if before.channel and not after.channel == before.channel and allbot:
        client = member.guild.voice_client
        if client:
            await client.disconnect()
            await before.channel.send('ボイスチャンネルからログアウトしました')

@tree.command(name="join", description="ボイスチャンネルに参加するよ")
async def join(interaction: Interaction):
    await interaction.response.defer()
    print(f"join:{interaction.channel}")
    connecting_channels.add(interaction.channel_id)
    await interaction.followup.send('ボイスチャンネルに参加します')
    try:
        await interaction.channel.connect()
    except Exception as e:
        connecting_channels.remove(interaction.channel_id)
        await interaction.followup.send(f"参加中に異常が発生しました\n```{e}```")

@tree.command(name="dj", description="ボイスチャンネルから退出するよ")
async def dc(interaction: Interaction):
    await interaction.response.defer()
    client: discord.VoiceClient | None = get_voice_client(
        interaction.channel_id)

    if client:
        await client.disconnect()
        await interaction.followup.send('ボイスチャンネルからログアウトしました')
    else:
        await interaction.followup.send('ボイスチャンネルに参加していません')

class nextbutton(ui.Button):
    def __init__(self, name: str, chanum: int):
        super().__init__(label=name)
        self.chanum=chanum
        self.name=name

    async def callback(self, interaction:Interaction):
        view=ui.View()
        i=0
        view.add_item(prevbutton("prev", i))
        for txt in metalist:
            if i >= 24:                             #change
                view.add_item(Charaname(txt, i))
            i+=1
        await interaction.response.edit_message(view=view)

class prevbutton(ui.Button):
    def __init__(self, name: str, chanum: int):
        super().__init__(label=name)
        self.chanum=chanum
        self.name=name

    async def callback(self, interaction:Interaction):
        view=ui.View()
        i=0
        for txt in metalist:
            if i < 24:
                view.add_item(Charaname(txt, i))
            elif i==24:
                view.add_item(nextbutton("next", i))
            i=i+1
        await interaction.response.edit_message(view=view)


class Charaname(ui.Button):
    def __init__(self, name: str,chanum: int):
        super().__init__(label=name)
        self.chanum = chanum
        self.name = name
    
    async def callback(self, interaction:Interaction):
        view = ui.View()
        for key, value in stylist3[self.chanum].items(): #key = id value = name
            view.add_item(style(value, key, self.name))
        await interaction.response.edit_message(content=f'{self.label}', view=view)

class style(ui.Button):
    def __init__(self, name: str, value: int, chaname:str):
        super().__init__(label=name)
        self.value=value
        self.chaname=chaname 

    async def callback(self, interaction: Interaction):
        namelist[interaction.user.name] = self.value
        if idlist[self.value] != None:
            with open('school.binaryfile', 'wb') as web:
                pickle.dump(namelist, web)
            await interaction.response.edit_message(content="変更しました", view=None)
            await interaction.followup.send(content=f'{interaction.user.name}を{self.chaname}の{self.label}に変更しました')

@tree.command(name="cha", description="キャラクターを変更するよ！")
async def cha(interaction: discord.Interaction):
    view = ui.View()
    i = 0
    for txt in metalist:
        if i < 24:                                      #change
            view.add_item(Charaname(txt, i))
        elif i==24:
            view.add_item(nextbutton("next", i))
        i=i+1
    await interaction.response.send_message("以下のボタンをクリックしてください：", view=view, ephemeral=True)
@tree.command(name="cha", description="キャラクターを変更するよ！")
async def cha(interaction: discord.Interaction):
    view = ui.View()
    i = 0
    for txt in metalist:
        if i < 23:
            view.add_item(Charaname(txt, i))
        else:
            view.add_item(nextbutton("next", i))
        i+=1
    await interaction.response.send_message("以下のボタンをクリックしてください：", view=view, ephemeral=True)

@tree.command(name="list", description="キャラクターのリストを表示するよ！")
async def list(interaction: discord.Interaction):
    await interaction.response.defer()
    #await interaction.followup.send(json_str)
    embed=discord.Embed(title="キャラリスト")  #metaar
    embed2=discord.Embed(title="キャラリスト2")
    for i in range(len(metalist)):
        if i < 25:
            embed.add_field(name=metalist[i], value=stylist2[i],inline = False)
        elif i < 50:
            embed2.add_field(name=metalist[i], value=stylist2[i],inline = False)
    await interaction.followup.send(embeds=[embed, embed2])

@tree.command(name="now", description="今のキャラクターを表示するよ！")
async def now(interaction: discord.Interaction):
    #global speaker_id
    await interaction.response.defer()
    await user_sep(interaction.user.name)
    await interaction.followup.send(str(idlist[namelist[interaction.user.name]])+"だよ！")
#client.run(TOKEN)

class usersel(ui.UserSelect):
    def __init__(self):
        super().__init__()

    async def callback(self, interaction:Interaction):
        await user_sep(self.values[0].name)
        await interaction.response.edit_message(content=f'{self.values[0].name}は{str(idlist[namelist[self.values[0].name]])}だよ！', view=None)

@tree.command(name="sel", description="ほかの人のキャラクターを表示するよ！")
async def sel(interaction:Interaction):    
    view = ui.View()
    view.add_item(usersel())
    await interaction.response.send_message("please select", view=view, ephemeral=True)   

async def main():
    # start the client
    async with bot:

        await bot.start(TOKEN)

asyncio.run(main())
