from pyteal import *
from functions.constants import *

def setup_dao_optins(funds_asset_id, shares_asset_id): return Seq(
    InnerTxnBuilder.Begin(),
    InnerTxnBuilder.SetFields(asset_optin(funds_asset_id)),
    InnerTxnBuilder.Next(),
    InnerTxnBuilder.SetFields(asset_optin(shares_asset_id)),
    InnerTxnBuilder.Submit()
)

def setup_image_nft(url_bytes):
    return Seq(
        App.globalPut(Bytes(GLOBAL_IMAGE_URL), url_bytes),
        inner_tx_and_submit({
            TxnField.type_enum: TxnType.AssetConfig,
            TxnField.asset_amount: Int(0),
            TxnField.config_asset_decimals: Int(0),
            TxnField.config_asset_total: Int(1),
            TxnField.config_asset_manager: Gtxn[0].sender(),
            TxnField.config_asset_default_frozen: Int(0),
            TxnField.config_asset_unit_name: Bytes("IMG"),
            TxnField.config_asset_name: Bytes("IMG"),
            TxnField.config_asset_url: url_bytes,
            TxnField.fee: Int(0)
        }),
        App.globalPut(Bytes(GLOBAL_IMAGE_ASSET_ID), InnerTxn.created_asset_id())
    )

def send_asset(receiver, id, amount): return Seq(
    inner_tx_and_submit(asset_xfer(receiver, id, amount))
)

# TODO why do tests fail if we use send_asset instead?,
# not clear why some txs have 0 fee and not others, might not have been intentional?
def send_asset_no_set_fee(receiver, id, amount): return Seq(
    inner_tx_and_submit(asset_xfer_no_set_fee(receiver, id, amount))
)

# conveniece to submit a single inner tx
def inner_tx_and_submit(fields): return Seq(
    InnerTxnBuilder.Begin(),
    InnerTxnBuilder.SetFields(fields),
    InnerTxnBuilder.Submit()
)

def asset_optin(asset_id): return {
    TxnField.type_enum: TxnType.AssetTransfer,
    TxnField.asset_receiver: Global.current_application_address(),
    TxnField.asset_amount: Int(0),
    TxnField.xfer_asset: asset_id,
    TxnField.fee: Int(0)
}

def asset_xfer(receiver, id, amount): return {
    TxnField.type_enum: TxnType.AssetTransfer,
    TxnField.asset_receiver: receiver,
    TxnField.asset_amount: amount,
    TxnField.xfer_asset: id,
    TxnField.fee: Int(0)
}

def asset_xfer_no_set_fee(receiver, id, amount): return {
    TxnField.type_enum: TxnType.AssetTransfer,
    TxnField.asset_receiver: receiver,
    TxnField.asset_amount: amount,
    TxnField.xfer_asset: id,
}


