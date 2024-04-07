import discord
import os
import requests
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta


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
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=key)

    if response.status_code == 200:
        data = response.json()

        # Convert the date to JST
        date_str = data['date']
        date_utc = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
        date_jst = date_utc + timedelta(hours=-4)
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

        embed.add_field(name="📅 Date (JST)", value=date_jst_str, inline=False)

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
        embeds = []
        current_embed = None

        for index, package in enumerate(packages, start=1):
            if index % 25 == 1:
                if current_embed:
                    embeds.append(current_embed)
                current_embed = discord.Embed(title='返礼品一覧', color=0XE16941, description='返礼品の一覧')

            package_name = package['name']
            package_price = package['price']
            package_category = package['category']['name']
            package_id = package['id']
            package_info = f"Price: {package_price}, ID: {package_id}, Category: {package_category}"
            current_embed.add_field(name=package_name, value=package_info, inline=False)

        if current_embed:
            embeds.append(current_embed)

        if embeds:
            for embed in embeds:
                await ctx.respond(embed=embed)
        else:
            await ctx.respond('No products found.')
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
        embed = discord.Embed(title=f'🔍Player Information for {tebex_id}')
        embed.add_field(name='👤Username', value=data['player']['username'])
        embed.add_field(name='🔨Ban Count', value=data['banCount'])
        embed.add_field(name='💳Chargeback Rate', value=data['chargebackRate'])
        total_purchases = '\n'.join([f"{currency}: {amount}" for currency, amount in data['purchaseTotals'].items()])
        embed.add_field(name='💵Total Purchases', value=total_purchases)

        # Recent payment histories
        payments = data['payments'][:5]  # Limit to the 5 most recent payments
        payment_info = ""
        for payment in payments:
            txn_id = payment.get('txn_id', 'N/A')
            timestamp = payment.get('time', 0)
            price = payment.get('price', 'N/A')
            currency = payment.get('currency', 'N/A')
            status = payment.get('status', 'N/A')

            # Convert the Unix timestamp to a datetime object
            dt = datetime.fromtimestamp(timestamp)

            # Add 9 hours to convert from UTC to JST
            jst_dt = dt + timedelta(hours=-4)

            # Format the datetime as a string in JST
            jst_time = jst_dt.strftime("%Y-%m-%d %H:%M:%S")

            payment_info += f"Transaction ID: {txn_id}\nPrice: {price} {currency}\nStatus: {status}\nDate (JST): {jst_time}\n\n"

        if payment_info:
            embed.add_field(name='Recent Payments', value=payment_info, inline=False)
        else:
            embed.add_field(name='Recent Payments', value='No recent payments found', inline=False)

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

@bot.slash_command(name='recentpayments', description='直近25件の決済の一覧表示')
@commands.check(is_admin)
async def recentpayments(ctx):
    url = 'https://plugin.tebex.io/payments?paged=1'
    key = {'X-Tebex-Secret': TEBEX_SECRET}
    response = requests.get(url, headers=key)

    if response.status_code == 200:
        data = response.json()
        payments = data['data'][:25]  # Truncate the list to the first 25 payments

        embed = discord.Embed(title='Recent Payments', color=discord.Color.blue())

        payment_info = ""
        for index, payment in enumerate(payments, start=1):
            transaction_id = payment.get('id', 'N/A')  # Use 'N/A' as default if 'id' is not found
            timestamp = payment.get('date', 0)  # Use 0 as default if 'date' is not found
            amount = payment.get('amount', 'N/A')  # Use 'N/A' as default if 'amount' is not found
            currency = payment.get('currency', {}).get('iso_4217', 'N/A')  # Use 'N/A' as default if 'currency' or 'iso_4217' is not found
            status = payment.get('status', 'N/A')  # Use 'N/A' as default if 'status' is not found
            player_name = payment.get('player', {}).get('name', 'N/A')  # Use 'N/A' as default if 'player' or 'name' is not found

            # Convert the timestamp to a datetime object
            dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")

            # Add 9 hours to convert from UTC to JST
            jst_dt = dt + timedelta(hours=-4)

            # Format the datetime as a string in JST
            jst_time = jst_dt.strftime("%Y-%m-%d %H:%M:%S")

            package_names = ', '.join([package.get('name', 'N/A') for package in payment.get('packages', [])])  # Use 'N/A' as default if 'packages' or 'name' is not found

            payment_info += f"**Transaction ID: {transaction_id}**\nPlayer: {player_name}\nAmount: {amount} {currency}\nPackage(s): {package_names}\nStatus: {status}\nDate (JST): {jst_time}\n\n"

            if index % 5 == 0 or index == len(payments):
                embed.add_field(name=f"Payments {index-4} to {index}", value=payment_info, inline=False)
                payment_info = ""

        embed.set_footer(text="Powered By NickyBoy", icon_url="https://i.imgur.com/QfmDKS6.png")
        await ctx.respond(embed=embed)
    else:
        await ctx.respond('Failed to retrieve recent payments.')
bot.run(TOKEN)
