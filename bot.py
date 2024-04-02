import discord
import os
import requests
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
TEBEX_SECRET = os.getenv('TEBEX_SECRET')
ADMIN_ROLE_IDS = [int(role_id) for role_id in os.getenv('ADMIN_ROLE_IDS').split(',')]

bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())

def is_admin(ctx):
    return any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)

@bot.slash_command(name='kakunin', description='Transaction IDから情報を取得')
@commands.check(is_admin)
async def kakunin(ctx, transaction_id: discord.Option(str, "tbxから始まるTransaction IDを入力")):
    url = f'https://plugin.tebex.io/payments/{transaction_id}'
    headers = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        embed = discord.Embed(title=f'Payment Information for Transaction ID: {transaction_id}')
        embed.add_field(name='Amount', value=data['amount'])
        embed.add_field(name='Status', value=data['status'])
        embed.add_field(name='Date', value=data['date'])
        embed.add_field(name='Player Name', value=data['player']['name'])
        package_names = ', '.join([package['name'] for package in data['packages']])
        embed.add_field(name='Package Name(s)', value=package_names)
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to retrieve payment information.')

@bot.slash_command(name='products', description='寄付できる返礼品の一覧')
@commands.check(is_admin)
async def products(ctx):
    url = 'https://plugin.tebex.io/packages'
    headers = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        packages = response.json()
        embed = discord.Embed(title='Available Products')
        for package in packages:
            embed.add_field(name=package['name'], value=f"Price: {package['price']}", inline=False)
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to retrieve product information.')

@bot.slash_command(name='search', description='Tebex IDから情報を取得')
@commands.check(is_admin)
async def search(ctx, tebex-id: discord.Option(str, "Tebex IDをここに入力 Transaction IDではない")):
    url = f'https://plugin.tebex.io/user/{tebex-id}'
    headers = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        embed = discord.Embed(title=f'Player Information for {tebex-id}')
        embed.add_field(name='Username', value=data['player']['username'])
        embed.add_field(name='Ban Count', value=data['banCount'])
        embed.add_field(name='Chargeback Rate', value=data['chargebackRate'])
        total_purchases = '\n'.join([f"{currency}: {amount}" for currency, amount in data['purchaseTotals'].items()])
        embed.add_field(name='Total Purchases', value=total_purchases)
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to retrieve player information.')

@bot.slash_command(name='updateproduct', description='返礼品の情報を更新')
@commands.check(is_admin)
async def updateproduct(ctx, package_id: discord.Option(int, "返礼品IDを入力 分からない場合は/productsで確認"), enabled: discord.Option(bool, "disabledの場合寄付の受け付けを中止"), name: discord.Option(str, "新しい返礼品の名前"), price: discord.Option(float, "新しい返礼品の価格")):
    url = f'https://plugin.tebex.io/package/{package_id}'
    headers = {'X-Tebex-Secret': TEBEX_SECRET}
    data = {
        'disabled': not enabled,
        'name': name,
        'price': price
    }
    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 204:
        status = 'enabled' if enabled else 'disabled'
        await ctx.respond(f'Package {package_id} has been updated. Status: {status}, Name: {name}, Price: {price}')
    else:
        await ctx.respond('Failed to update the package.')

@bot.slash_command(name='createurl', description='決済URLを作成')
@commands.check(is_admin)
async def createurl(ctx, package_id: discord.Option(str, "返礼品IDを入力 分からない場合は/productsで確認"), tebex_id: discord.Option(str, "Tebex IDを入力")):
    url = 'https://plugin.tebex.io/checkout'
    headers = {'X-Tebex-Secret': TEBEX_SECRET}
    data = {
        'package_id': package_id,
        'username': tebex_id
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        checkout_data = response.json()
        checkout_url = checkout_data['url']
        expires_at = checkout_data['expires']
        embed = discord.Embed(title='Checkout URL Created', color=discord.Color.green())
        embed.add_field(name='URL', value=checkout_url)
        embed.add_field(name='Expires At', value=expires_at)
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to create the checkout URL.')

bot.run(TOKEN)
