from discord.ext import commands

class COG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_message = """
```
คำสั่งเล่นเพลง:
$play <ชื่อเพลง หรือ urlของเพลงจากyt> - เล่นเพลงนั้นใน voice channel ที่เราอยู่
$queue - แสดง playlist ทั้งหมด
$skip - ข้ามเพลงปัจจุบัน
$stop - เป็นคำสั่งเอาบอทออกจาก voice channel
$pause - เป็นคำสั่งเพื่อหยุดเพลงชั่วคราว
$resume - เป็นคำสั่งเพื่อเล่นเพลงต่อ
$cq - เป็นคำสั่งที่ใช้ลบเพลงทั้งหมดใน playlist 
⏯ - กดปุ่มนี้เพื่อหยุดเพลงชั่วคราว/เล่นต่อ
⏭ - กดปุ่มนี้เพื่อข้ามเพลงปัจจุบัน
```
"""
        self.text_channel_list = []

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot Online!!") 

    @commands.command(name="help", help="Displays all the available commands")
    async def help(self, ctx):
        await ctx.send(self.help_message)