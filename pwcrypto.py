# Fix for Python 3.13 (Render removing imghdr)
import sys, types
if sys.version_info >= (3, 13):
    sys.modules["imghdr"] = types.ModuleType("imghdr")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import re, random, string

# ==========================
# CONFIGURATION
#  ==========================

BOT_TOKEN = "8378636411:AAFMAkSSyB5G6EPoxmNd10hx6QFh3pRV4BA"

# Admins (numeric Telegram user IDs)
ADMINS = [5229586098, 7962772947, 7880967664, 910096684, 5825027777, 6864194951, 6999316166, 2001575810]  # @A812sss, @iJorvi, @ig_sadhowop

# Active deals in memory
active_deals = {}

# ==========================
# HELPER FUNCTIONS
# ==========================

def generate_trade_id():
    """Generate a random Trade ID."""
    chars = string.ascii_uppercase + string.digits
    return "#TID" + "".join(random.choices(chars, k=6))

def parse_deal_text(text):
    """Extract deal info from the format message."""
    buyer = re.search(r"BUYER\s*:\s*(@\w+)", text, re.IGNORECASE)
    seller = re.search(r"SELLER\s*:\s*(@\w+)", text, re.IGNORECASE)
    amount = re.search(r"DEAL AMOUNT\s*:\s*\$?([\d.]+)", text, re.IGNORECASE)
    return {
        "buyer": buyer.group(1) if buyer else None,
        "seller": seller.group(1) if seller else None,
        "amount": float(amount.group(1)) if amount else None
    }

# ==========================
# /ADD COMMAND
# ==========================

async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when admin replies with /add."""
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to a deal message that follows your format to use /add.")
        return

    user = update.message.from_user
    print(f"DEBUG: Triggered by {user.username} (ID: {user.id})")

    if user.id not in ADMINS:
        await update.message.reply_text(f"🚫 Only authorized admins can add deals.\n\nYour ID: {user.id}")
        return

    deal_text = update.message.reply_to_message.text
    info = parse_deal_text(deal_text)

    if not info["buyer"] or not info["seller"] or not info["amount"]:
        await update.message.reply_text("❌ Could not parse deal details. Make sure your message matches this format:\n\n"
                                        "DEAL INFO : USD INR EXCHANGE\nBUYER : @username\nSELLER : @username\nDEAL AMOUNT : $100\nTIME TO COMPLETE DEAL :")
        return

    # Create and store temporary deal data
    trade_id = generate_trade_id()
    active_deals[trade_id] = {
        "buyer": info["buyer"],
        "seller": info["seller"],
        "deal_amount": info["amount"],
        "escrow_admin": f"@{user.username}" if user.username else f"ID:{user.id}"
    }

    # Inline keyboard for fee selection
    keyboard = [
        [
            InlineKeyboardButton("0.7% fees", callback_data=f"fee_0.7_{trade_id}"),
            InlineKeyboardButton("1% fees", callback_data=f"fee_1_{trade_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_to_message.reply_text(
        f"Please select the fees for this deal:",
        reply_markup=reply_markup
    )

# ==========================
# FEE SELECTION HANDLER
# ==========================

async def fee_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when one of the fee buttons is pressed."""
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    fee_percent = float(data[1])
    trade_id = data[2]

    deal = active_deals.get(trade_id)
    if not deal:
        await query.edit_message_text("⚠️ Deal not found. Please try again.")
        return

    deal_amount = deal["deal_amount"]
    fee = round(deal_amount * (fee_percent / 100), 2)
    release_amount = round(deal_amount - fee, 2)

    # Store final deal data
    deal["fee_percent"] = fee_percent
    deal["fee_amount"] = fee
    deal["release_amount"] = release_amount

    msg = (
        f"💰 Deal Amount: ${deal_amount:.2f}\n"
        f"📤 Received Amount: ${deal_amount:.2f}\n"
        f"📤 Release/Refund Amount: ${release_amount:.2f}\n"
        f"🆔 Trade ID: {trade_id}\n\n"
        f"👤 Buyer: {deal['buyer']}\n"
        f"👤 Seller: {deal['seller']}\n\n"
        f"🛡 Escrowed By: {deal['escrow_admin']}"
    )

    await query.edit_message_text(msg)

# ==========================
# /CLOSE COMMAND
# ==========================

async def close_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when admin closes a deal."""
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to a deal message to use /close.")
        return

    user = update.message.from_user
    print(f"DEBUG: Close triggered by {user.username} (ID: {user.id})")

    if user.id not in ADMINS:
        await update.message.reply_text("🚫 Only authorized admins can close deals.")
        return

    replied_text = update.message.reply_to_message.text

    # 1️⃣ Try to find Trade ID in replied message
    trade_id_match = re.search(r"#TID[A-Z0-9]+", replied_text)

    # 2️⃣ If not found, try to find a matching active deal based on buyer/seller text
    if not trade_id_match:
        found_id = None
        for tid, deal in active_deals.items():
            if (deal["buyer"] and deal["buyer"] in replied_text) or (deal["seller"] and deal["seller"] in replied_text):
                found_id = tid
                break
        if found_id:
            trade_id = found_id
        else:
            await update.message.reply_text("❌ Could not find Trade ID in that deal.")
            return
    else:
        trade_id = trade_id_match.group(0)

    deal = active_deals.get(trade_id)
    if not deal:
        await update.message.reply_text("⚠️ No record found for this trade.")
        return

    msg = (
        f"✅ Deal  Completed\n"
        f"🆔 Trade ID: {trade_id}\n"
        f"📤 Released: ${deal['release_amount']:.2f}\n"
        f"ℹ️ Total Released: ${deal['release_amount']:.2f}\n\n"
        f"👤 Buyer: {deal['buyer']}\n"
        f"👤 Seller: {deal['seller']}\n\n"
        f"🛡 Escrowed By: {deal['escrow_admin']}\n"
    )

    await update.message.reply_to_message.reply_text(msg)

    # Remove from active deals
    del active_deals[trade_id]

# ==========================
# MAIN FUNCTION
# ==========================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("add", add_deal))
    app.add_handler(CallbackQueryHandler(fee_selected, pattern=r"^fee_"))
    app.add_handler(CommandHandler("close", close_deal))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
