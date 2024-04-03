import discord
import os
import requests
import json
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
TEBEX_SECRET = os.getenv('TEBEX_SECRET')
ADMIN_ROLE_IDS = [int(role_id) for role_id in os.getenv('ADMIN_ROLE_IDS').split(',')]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Create a dictionary to store apartment data
apartments = {}

def save_apartments():
    # Save the apartments data to a file
    with open('apartments.json', 'w') as file:
        json.dump(apartments, file)

def load_apartments():
    # Load the apartments data from a file
    try:
        with open('apartments.json', 'r') as file:
            apartments.update(json.load(file))
    except FileNotFoundError:
        pass

def is_admin(ctx):
    return any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)

@bot.slash_command(name='kakunin', description='Transaction IDから情報を取得')
@commands.check(is_admin)
async def kakunin(ctx, transaction_id: discord.Option(str, "tbxから始まるTransaction IDを入力")):
    url = f'https://plugin.tebex.io/payments/{transaction_id}'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=key)

    if response.status_code == 200:
        data = response.json()

        # Convert the date to JST
        date_str = data['date']
        date_utc = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
        date_jst = date_utc + timedelta(hours=9)
        date_jst_str = date_jst.strftime("%Y-%m-%d %H:%M:%S")

        embed = discord.Embed(
            title=f"🔍 Information for {transaction_id}",
            description="Here are the details of the transaction:",
            color=discord.Color.blue()
        )

        embed.add_field(name="💰 Price", value=data['amount'], inline=True)

        status = data['status']
        if status.lower() == 'complete':
            status_text = f"```🟢 {status}```"
        else:
            status_text = f"```🔴 {status}```"
        embed.add_field(name="📊 Status", value=status_text, inline=True)

        embed.add_field(name="📅 Date (JST)", value=date_jst_str)

        player_name = data['player']['name']
        embed.add_field(name="👤 Tebex Username", value=player_name, inline=False)

        package_names = ', '.join([package['name'] for package in data['packages']])
        embed.add_field(name="🎁 Package Name(s)", value=package_names, inline=False)

        embed.set_footer(
            text="Powered By NickyBoy",
            icon_url="https://i.imgur.com/QfmDKS6.png"
        )

        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to retrieve payment information.')

@bot.slash_command(name='products', description='寄付できる返礼品の一覧')
@commands.check(is_admin)
async def products(ctx):
    url = 'https://plugin.tebex.io/packages'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=key)

    if response.status_code == 200:
        packages = response.json()
        embed = discord.Embed(title='返礼品一覧', color=0XE16941, description='返礼品の一覧')
        for package in packages:
            package_name = package['name']
            package_price = package['price']
            package_category = package['category']['name']
            package_id = package['id']
            package_info = f"Price: {package_price}, ID: {package_id}, Category: {package_category}"
            embed.add_field(name=package_name, value=package_info, inline=False)
            embed.set_footer(text="Powered By NickyBoy", icon_url="https://i.imgur.com/QfmDKS6.png")
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to retrieve product information.')

@bot.slash_command(name='search', description='Tebex IDから情報を取得')
@commands.check(is_admin)
async def search(ctx, tebex_id: discord.Option(str, "Tebex IDをここに入力 Transaction IDではない")):
    url = f'https://plugin.tebex.io/user/{tebex_id}'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=key)

    if response.status_code == 200:
        data = response.json()
        embed = discord.Embed(title=f'Player Information for {tebex_id}')
        embed.add_field(name='Username', value=data['player']['username'])
        embed.add_field(name='Ban Count', value=data['banCount'])
        embed.add_field(name='Chargeback Rate', value=data['chargebackRate'])
        total_purchases = '\n'.join([f"{currency}: {amount}" for currency, amount in data['purchaseTotals'].items()])
        embed.add_field(name='Total Purchases', value=total_purchases)
        embed.set_footer(text="Powered By NickyBoy", icon_url="https://i.imgur.com/QfmDKS6.png")
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to retrieve player information.')

@bot.slash_command(name='updateproduct', description='返礼品の情報を更新')
@commands.check(is_admin)
async def updateproduct(ctx, package_id: discord.Option(int, "返礼品IDを入力 分からない場合は/productsで確認"), enabled: discord.Option(bool, "disabledの場合寄付の受け付けを中止"), name: discord.Option(str, "新しい返礼品の名前"), price: discord.Option(float, "新しい返礼品の価格")):
    url = f'https://plugin.tebex.io/package/{package_id}'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    data = {
        'disabled': not enabled,
        'name': name,
        'price': price
    }
    response = requests.put(url, headers=key, json=data)

    if response.status_code == 204:
        status = 'enabled' if enabled else 'disabled'
        await ctx.respond(f'Package {package_id} has been updated. Status: {status}, Name: {name}, Price: {price}')
    else:
        await ctx.respond('Failed to update the package.')

@bot.slash_command(name='createurl', description='決済URLを作成')
@commands.check(is_admin)
async def createurl(ctx, package_id: discord.Option(str, "返礼品IDを入力 分からない場合は/productsで確認"), tebex_id: discord.Option(str, "Tebex IDを入力")):
    url = 'https://plugin.tebex.io/checkout'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    data = {
        'package_id': package_id,
        'username': tebex_id
    }
    response = requests.post(url, headers=key, json=data)

    if response.status_code == 201:
        checkout_data = response.json()
        checkout_url = checkout_data['url']
        expires_at = checkout_data['expires']
        embed = discord.Embed(title='Checkout URL Created', color=discord.Color.green())
        embed.add_field(name='URL', value=checkout_url)
        embed.add_field(name='Expires At', value=expires_at)
        embed.set_footer(text="Powered By NickyBoy", icon_url="https://i.imgur.com/QfmDKS6.png")
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to create the checkout URL.')

@bot.slash_command(name='createhouse', description='Create a new apartment')
@commands.check(is_admin)
async def createhouse(ctx, name: str, max_residents: int):
    if name in apartments:
        await ctx.respond(f"An apartment with the name '{name}' already exists.")
    else:
        apartments[name] = {
            'max_residents': max_residents,
            'current_residents': 0,
            'waiting_list': 0
        }
        save_apartments()
        await ctx.respond(f"Apartment '{name}' created successfully.")

@bot.slash_command(name='addresidents', description='Add new residents to an apartment')
@commands.check(is_admin)
async def addresidents(ctx, name: str, num_residents: int):
    if name not in apartments:
        await ctx.respond(f"Apartment '{name}' does not exist.")
    else:
        apartment = apartments[name]
        available_slots = apartment['max_residents'] - apartment['current_residents']
        if num_residents <= available_slots:
            apartment['current_residents'] += num_residents
            save_apartments()
            await ctx.respond(f"{num_residents} resident(s) added to apartment '{name}'.")
        else:
            apartment['current_residents'] = apartment['max_residents']
            apartment['waiting_list'] += num_residents - available_slots
            save_apartments()
            await ctx.respond(f"{available_slots} resident(s) added to apartment '{name}'. {num_residents - available_slots} resident(s) added to the waiting list.")

@bot.slash_command(name='vipapartment', description='Show a list of apartments')
@commands.check(is_admin)
async def vipapartment(ctx):
    if not apartments:
        await ctx.respond("No apartments found.")
    else:
        embed = discord.Embed(title='VIP Apartments', color=discord.Color.blue())
        for name, apartment in apartments.items():
            embed.add_field(
                name=name,
                value=f"Max Residents: {apartment['max_residents']}\nCurrent Residents: {apartment['current_residents']}\nWaiting List: {apartment['waiting_list']}",
                inline=False
            )
        await ctx.respond(embed=embed)

# Load the apartments data when the bot starts
load_apartments()

bot.run(TOKEN)
