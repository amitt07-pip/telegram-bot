from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

ADMINS = [5229586098, 7962772947, 7880967664]
BOT_TOKEN = "8378636411:AAFMAkSSyB5G6EPoxmNd10hx6QFh3pRV4BA"

# Step 1: /add command - ask for deal info
async def add_deal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMINS:
        await update.message.reply_text("🚫 Only authorized admins can add deals.")
        return
    await update.message.reply_text(
        "Please send deal info in this format:\n\n"
        "DEAL INFO : \nBUYER : \nSELLER : \nDEAL AMOUNT : $\nTIME TO COMPLETE DEAL :"
    )

# Step 2: Handle deal info message
async def deal_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    info = {"buyer": None, "seller": None, "amount": None}

    # Extract buyer, seller, amount
    import re
    buyer = re.search(r"BUYER\s*:\s*@?(\w+)", text, re.IGNORECASE)
    seller = re.search(r"SELLER\s*:\s*@?(\w+)", text, re.IGNORECASE)
    amount = re.search(r"DEAL AMOUNT\s*:\s*\$?([\d.]+)", text, re.IGNORECASE)

    if buyer: info["buyer"] = buyer.group(1)
    if seller: info["seller"] = seller.group(1)
    if amount: info["amount"] = float(amount.group(1))

    context.user_data["deal_info"] = info  # ✅ store info for later use

    keyboard = [
        [InlineKeyboardButton("0.7% fees", callback_data="fee:0.7"),
         InlineKeyboardButton("1% fees", callback_data="fee:1.0")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select the fee percentage:", reply_markup=markup)

# Step 3: Handle fee selection
async def fee_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fee_percent = float(query.data.split(":")[1])

    info = context.user_data.get("deal_info")  # ✅ retrieve saved info
    if not info:
        await query.edit_message_text("⚠️ No deal info found. Please start again with /add.")
        return

    # Example buyer/seller IDs (you can add actual lookup logic if needed)
    buyer_id = 7977014658
    seller_id = 1361170893

    message = (
        f"💰 Deal Amount: ${info['amount']:.2f}\n"
        f"💵 Received Amount: ${info['amount']:.2f}\n"
        f"💸 Release/Refund Amount: ${info['amount'] * (1 - fee_percent/100):.2f}\n"
        f"🆔 Trade ID: #TIDXXXXXX\n\n"
        f"Continue the Deal\n"
        f"👤 Buyer: @{info['buyer']} [{buyer_id}]\n"
        f"🏷 Seller: @{info['seller']} [{seller_id}]\n\n"
        f"🛡 Escrowed By: @jorvi"
    )

    await query.edit_message_text(message)

# --- Main setup ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("add", add_deal))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, deal_info))
app.add_handler(CallbackQueryHandler(fee_selected))

app.run_polling()

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
