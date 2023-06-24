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

voice_styles = []
voice_style_dict = []
idlist = {}
fixedlist = []

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
    item = [source, filename]
    queue.append(item)
    if not voice_client:
        return
    if not voice_client.is_playing():
        play(voice_client, queue)


def play(voice_client: discord.VoiceClient, queue: deque):
    if not queue or voice_client.is_playing():
        return
    # item = [source, filename]
    item = queue.popleft()
    voice_client.play(item[0], after=lambda e: play(voice_client, queue))

def replace_stamp(text: str) -> str:
    text = re.sub('<:([^:]*):.*>', '\\1', text)
    return text

async def replace_user_name(text: str) -> str:
    for word in text.split():
        if not mention.match(word):
            continue
        print(word)
        user_id = re.sub('<@([^>]*)>', '\\1', word)
        print(user_id)
        user_name = str(await bot.fetch_user(user_id))
        user_name = re.sub('#.*', '', user_name)
        text = text.replace(word, '@' + user_name)
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
        text = replace_stamp(text)
    if mention.search(text):
        text = await replace_user_name(text)
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

async def load_metas():
    # METAS[]の要素のmeta[] の styleプロパティを取得
    for meta in METAS:
        metalist.append(meta.name)
        style_list = []
        style_dic = {}
        for style in meta.styles:
            style_list.append(style.name + "  " + str(style.id))
            style_dic.setdefault(style.id, style.name)
            idlist[style.id] = meta.name + '  ' +style.name
        voice_styles.append(copy.deepcopy(style_list))
        voice_style_dict.append(copy.deepcopy(style_dic))

@bot.event
async def on_ready():
    global namelist 
    #await client.get_channel(channel).connect()
    await tree.sync()   
    await load_metas()
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


class CharacterSelectButton(ui.Button):
    def __init__(self, name: str, num: int):
        super().__init__(label=name)
        self.num = num
        self.name = name

    async def callback(self, interaction:Interaction):
        view = ui.View()
        for key, value in voice_style_dict[self.num].items(): #key = style.id, value = style.name
            view.add_item(VoiceStyleSelectButton(value, key, self.name))
        await interaction.response.edit_message(content=f'{self.label}', view=view)

# ノーマル とか ツンツン とか あまあま とか
class VoiceStyleSelectButton(ui.Button):
    def __init__(self, style_name: str, style_id: int, chaname:str):
        super().__init__(label=style_name)
        self.style=style_id
        self.character_name=chaname

    async def callback(self, interaction: Interaction):
        namelist[interaction.user.name] = self.style
        if idlist[self.style] != None:
            with open('school.binaryfile', 'wb') as web:
                pickle.dump(namelist, web)
            await interaction.response.edit_message(content=f'{interaction.user.name}を{self.character_name}の{self.label}に変更しました', view=None)

@tree.command(name="cha", description="キャラクターを変更するよ！")
async def character_select_command(interaction: discord.Interaction):
    character_select_buttons = ui.View()
    for i, txt in enumerate(metalist):
        character_select_buttons.add_item(CharacterSelectButton(txt, i))
    await interaction.response.send_message("以下のボタンをクリックしてください：", view=character_select_buttons, ephemeral=True)

@tree.command(name="list", description="キャラクターのリストを表示するよ！")
async def display_character_list_command(interaction: discord.Interaction):
    await interaction.response.defer()
    embed=discord.Embed(title="キャラリスト")
    for i in range(len(metalist)):
        embed.add_field(name=metalist[i], value=voice_styles[i], inline = False)
    await interaction.followup.send(embed=embed)

@tree.command(name="now", description="今のキャラクターを表示するよ！")
async def now(interaction: discord.Interaction):
    #global speaker_id
    await interaction.response.defer()
    await user_sep(interaction.user.name)
    await interaction.followup.send(str(idlist[namelist[interaction.user.name]])+"だよ！")
#client.run(TOKEN)

class UserSelect(ui.UserSelect):
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
