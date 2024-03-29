import discord
import requests
import json
from discord import Embed, Interaction, ui
import os
from discord.ext import commands
import asyncio
from collections import defaultdict, deque
import re
import random
import copy
import pickle
import queue

METAS = ""
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

host = os.environ["ENGINE_HOST"]
port = os.environ["ENGINE_PORT"]

# speaker_id = 3

TOKEN = os.environ["DISCORD_TOKEN"]
intents = discord.Intents.all()
client = discord.Client(intents=intents)
queue_dict = defaultdict(deque)
connecting_channels = set()
url = re.compile('^http')
mention = re.compile('<@[^>]*>')
stamp = re.compile('<:([^:]*):.*>')

guild = os.environ["DISCORD_GUILD"]
# guild = 945735786739933275 #自分鯖
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

playAudioQueue = queue.Queue()


def enqueue(voice_client: discord.VoiceClient, guild: discord.guild, source, filename: str):
    global playAudioQueue
    playAudioQueue.put([source, filename])
    if not voice_client:
        return
    if not voice_client.is_playing():
        play(voice_client)
        
def play(voice_client: discord.VoiceClient):
    global playAudioQueue
    if playAudioQueue.empty():
        return
    source, filename = playAudioQueue.get()
    voice_client.play(source, after=lambda e: [os.remove(filename), play(voice_client)])


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


async def vvox_test(text) -> str:
    global speaker_id
    params = (
        ('text', text),
        ('speaker', speaker_id),
    )
    query = requests.post(
        f'http://{host}:{port}/audio_query',
        params=params
    )
    synthesis = requests.post(
        f'http://{host}:{port}/synthesis',
        headers={"Content-Type": "application/json"},
        params=params,
        data=json.dumps(query.json())
    )
    # make random file name
    filename = ''.join([random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for i in range(10)]) + '.mp3'
    with open(filename, mode='wb') as f:
        f.write(synthesis.content)
        return filename


def get_voice_client(channel_id: int) -> discord.VoiceClient | None:
    for client in bot.voice_clients:
        if client.channel.id == channel_id:
            return client
    else:
        return None


async def user_sep(user_name: str) -> str:
    global namelist
    if namelist.get(user_name) == None:
        namelist.setdefault(user_name, random.randint(0, len(idlist)-1))
        with open('school.binaryfile', 'wb') as web:
            pickle.dump(namelist, web)


async def text_check(text: str, user_name: str) -> str:
    # print(text)
    global speaker_id
    if len(text) > 100:
        raise Exception("文字数が長すぎるよ")
    if stamp.search(text):
        text = replaceStamp(text)
    if mention.search(text):
        text = await replaceUserName(text)
    # text = re.sub('#.*', '', str(user_name)) + ' ' + text
    text = re.sub('http.*', '', text)
    match = re.findall(r'[a-zA-Z0-9ぁ-んァ-ン一-龥]', text)
    if match == []:
        # return await bot.process_commands(text)
        return
    # text = replaceDict(text)
    if len(text) > 100:
        raise Exception("文字数が長すぎるよ")
    await user_sep(user_name)
    speaker_id = namelist[user_name]
    filename = await vvox_test(text)
    if os.path.getsize(filename) > 10000000:
        raise Exception("再生時間が長すぎるよ")
    return text, filename


async def listmk():
    speakerResponse:requests.Response = requests.get(f'http://{host}:{port}/speakers',
                         headers={"Content-Type": "application/json"}).content.decode()
    speakerList = json.loads(speakerResponse)
    for meta in speakerList:
        metalist.append(meta["name"])
        for style in meta["styles"]:
            stylist1.append(style["name"] + "  " + str(style["id"]))
            stylist4.setdefault(style["id"], style["name"])
            idlist[style["id"]] = meta["name"] + '  ' + style["name"]
        st = copy.copy(stylist1)
        sts = copy.copy(stylist4)
        stylist2.append(st)
        stylist3.append(sts)
        stylist1.clear()
        stylist4.clear()


@bot.event
async def on_ready():
    global namelist
    # await client.get_channel(channel).connect()
    await tree.sync()
    await listmk()
    with open('school.binaryfile', 'rb') as web:
        namelist = pickle.load(web)
    print('connected')


@bot.event
async def on_message(message: discord.Message):
    # if message.author.bot:
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
        # await message.channel.send(e)
        return await bot.process_commands(message)

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
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    allbot = True
    selfcheck = False
    for mem in before.channel.members:
        if mem.id == bot.user.id:
            selfcheck = True
        if not mem.bot:
            allbot = False
    if before.channel and allbot and selfcheck:
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
        self.chanum = chanum
        self.name = name

    async def callback(self, interaction: Interaction):
        view = ui.View()
        i = 0
        view.add_item(prevbutton("prev", i))
        for txt in metalist:
            if i >= 24:  # change
                view.add_item(Charaname(txt, i))
            i += 1
        await interaction.response.edit_message(view=view)


class prevbutton(ui.Button):
    def __init__(self, name: str, chanum: int):
        super().__init__(label=name)
        self.chanum = chanum
        self.name = name

    async def callback(self, interaction: Interaction):
        view = ui.View()
        i = 0
        for txt in metalist:
            if i < 24:
                view.add_item(Charaname(txt, i))
            elif i == 24:
                view.add_item(nextbutton("next", i))
            i = i+1
        await interaction.response.edit_message(view=view)


class Charaname(ui.Button):
    def __init__(self, name: str, chanum: int):
        super().__init__(label=name)
        self.chanum = chanum
        self.name = name

    async def callback(self, interaction: Interaction):
        view = ui.View()
        for key, value in stylist3[self.chanum].items():  # key = id value = name
            view.add_item(style(value, key, self.name))
        await interaction.response.edit_message(content=f'{self.label}', view=view)


class style(ui.Button):
    def __init__(self, name: str, value: int, chaname: str):
        super().__init__(label=name)
        self.value = value
        self.chaname = chaname

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
        if i < 24:  # change
            view.add_item(Charaname(txt, i))
        elif i == 24:
            view.add_item(nextbutton("next", i))
        i = i+1
    await interaction.response.send_message("以下のボタンをクリックしてください：", view=view, ephemeral=True)


@tree.command(name="charalist", description="キャラクターのリストを表示するよ！")
async def charalist(interaction: discord.Interaction):
    await interaction.response.defer()
    # await interaction.followup.send(json_str)
    embed = discord.Embed(title="キャラリスト")  # metaar
    embed2 = discord.Embed(title="キャラリスト2")
    for i in range(len(metalist)):
        if i < 25:
            embed.add_field(name=metalist[i], value=stylist2[i], inline=False)
        elif i < 50:
            embed2.add_field(name=metalist[i], value=stylist2[i], inline=False)
    await interaction.followup.send(embeds=[embed, embed2])


@tree.command(name="now", description="今のキャラクターを表示するよ！")
async def now(interaction: discord.Interaction):
    await interaction.response.defer()
    voicemembers = interaction.channel.voice_states
    if not voicemembers:
        await interaction.followup.send("誰もチャンネルに参加していないよ！")
    else:
        embed = discord.Embed(title="参加者のキャラはこうなっているよ！")
        for memberid in voicemembers.keys():
            user = await bot.fetch_user(memberid)
            await user_sep(str(user.name))
            embed.add_field(name=user.display_name, value=str(
                idlist[namelist[str(user.name)]]), inline=False)
        await interaction.followup.send(embed=embed)


@tree.command(name="voicelist", description="今このサーバーではみんなの声がこうなっているよ")
async def voicelist(interaction: Interaction):
    await interaction.response.defer()
    embed = Embed(title="全員のリストだよ")
    for key, value in namelist.items():
        embed.add_field(name=key, value=str(idlist[value]), inline=False)
    await interaction.followup.send(embed=embed)


class usersel(ui.UserSelect):
    def __init__(self):
        super().__init__()

    async def callback(self, interaction: Interaction):
        await user_sep(self.values[0].name)
        await interaction.response.edit_message(content=f'{self.values[0].name}は{str(idlist[namelist[self.values[0].name]])}だよ！', view=None)


class delbutton(ui.Button):
    def __init__(self, name):
        super().__init__(label=str(name))
        self.name = name

    async def callback(self, interaction: Interaction):
        if self.name == "next":
            view = ui.View()
            i = 0
            for key in namelist.keys():
                i += 1
                if i == 24:
                    view.add_item(delbutton("prev"))
                elif 24 < i < 51:
                    view.add_item(delbutton(key))
            await interaction.response.edit_message(view=view)
        elif self.name == "prev":
            view = ui.View()
            i = 0
            for key in namelist.keys():
                i += 1
                if i < 25:
                    view.add_item(delbutton(key))
                elif i == 25:
                    view.add_item(delbutton("next"))
            await interaction.response.edit_message(view=view)
        else:
            namelist.pop(self.name)
            with open('school.binaryfile', 'wb') as web:
                pickle.dump(namelist, web)
        await interaction.response.edit_message(content=f'{self.name}を削除したよ!', view=None)


@tree.command(name="delete", description="消去用")
async def delete(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id == 620830778145636358 or interaction.user.id == 436414915755114507:
        view = ui.View()
        i = 0
        for key in namelist.keys():
            i += 1
            if i < 25:
                view.add_item(delbutton(key))
            elif i == 25:
                print(key)
                view.add_item(delbutton("next"))
                break
        await interaction.followup.send("消したい人を選んでね！", view=view)
    else:
        await interaction.followup.send("お前にその権限はない")


@tree.command(name="sel", description="ほかの人のキャラクターを表示するよ！")
async def sel(interaction: Interaction):
    view = ui.View()
    view.add_item(usersel())
    await interaction.response.send_message("please select", view=view, ephemeral=True)


@tree.command(name="onani", description="ボイスチャンネルに参加するよ")
async def onani(interaction: Interaction):
    await interaction.response.defer()
    client: discord.VoiceClient | None = get_voice_client(
        interaction.channel_id)

    if client:
        await client.disconnect()
        print(f"join:{interaction.channel}")
        connecting_channels.add(interaction.channel_id)
        await interaction.followup.send('参加しなおしました')
        try:
            await interaction.channel.connect()
        except Exception as e:
            connecting_channels.remove(interaction.channel_id)
            await interaction.followup.send(f"参加中に異常が発生しました\n```{e}```")
    else:
        await interaction.followup.send('ボイスチャンネルに参加していません')


async def main():
    # start the client
    async with bot:

        await bot.start(TOKEN)

asyncio.run(main())
