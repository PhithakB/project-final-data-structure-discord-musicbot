from discord.ext import commands
from cog import COG
from music import MUSIC

#ตั้งค่าให้ใช้ prefix เป็น $
bot = commands.Bot(command_prefix='$')

#ลบคำสั่ง help ที่เป็นค่าเริ่มต้นเพื่อจะได้ตั้งค่าเอง
bot.remove_command('help')

#เรียกใช้ class จากไฟล์ที่ import เข้ามา
bot.add_cog(COG(bot))
bot.add_cog(MUSIC(bot))

#เป็น token ของบอท discord
bot.run("OTAxMDQxNzI3Mjc0NjQ3NTcz.YXKGgA.xWwyZxUc5H5xoCWPVvcJTDmHNJA")