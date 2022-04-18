from pyteal import *

"""Investing escrow"""

tmpl_share_price = Tmpl.Int("TMPL_SHARE_PRICE")
tmpl_central_app_id = Tmpl.Int("TMPL_CENTRAL_APP_ID")
tmpl_funds_asset_id = Tmpl.Int("TMPL_FUNDS_ASSET_ID")
tmpl_shares_asset_id = Tmpl.Int("TMPL_SHARES_ASSET_ID")
tmpl_app_escrow_address = Tmpl.Addr("TMPL_APP_ESCROW_ADDRESS")

GLOBAL_RECEIVED_TOTAL = "ReceivedTotal"
LOCAL_CLAIMED_TOTAL = "ClaimedTotal"
LOCAL_SHARES = "Shares"

def program():
    handle_setup_dao = Seq(
        # creator sends min balance to app address
        Assert(Gtxn[0].type_enum() == TxnType.Payment),
        Assert(Gtxn[0].receiver() == tmpl_app_escrow_address),
        
        # app call
        Assert(Gtxn[1].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[1].application_id() == tmpl_central_app_id),
        Assert(Gtxn[1].on_completion() == OnComplete.NoOp),
        Assert(Gtxn[1].application_args.length() == Int(12)),

        # creator sends min balance to customer escrow
        Assert(Gtxn[2].type_enum() == TxnType.Payment),
        Assert(Gtxn[2].receiver() == Gtxn[1].application_args[0]),

        # creator sends min balance to investing escrow
        Assert(Gtxn[3].type_enum() == TxnType.Payment),

        # investing escrow opt-ins to shares
        Assert(Gtxn[4].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[4].asset_amount() == Int(0)),

        # customer escrow opt-ins to funds asset
        Assert(Gtxn[5].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[5].asset_amount() == Int(0)),

        # creator transfers shares to investing escrow
        Assert(Gtxn[6].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[6].xfer_asset() == Btoi(Gtxn[1].application_args[2])),

        Approve()
    )

    handle_invest = Seq(
        Assert(Global.group_size() == Int(4)),

        # app call to initialize shares state
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),
        Assert(Gtxn[0].application_id() == tmpl_central_app_id),
        Assert(Gtxn[0].application_args.length() == Int(2)),

        # shares xfer to investor
        Assert(Gtxn[1].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[1].asset_amount() > Int(0)),
        Assert(Gtxn[1].xfer_asset() == tmpl_shares_asset_id),
        Assert(Gtxn[1].asset_receiver() == tmpl_app_escrow_address), 
        Assert(Gtxn[1].fee() == Int(0)),
        Assert(Gtxn[1].asset_close_to() == Global.zero_address()),
        Assert(Gtxn[1].rekey_to() == Global.zero_address()),

        # investor pays for shares: funds xfer to app escrow
        Assert(Gtxn[2].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[2].asset_amount() > Int(0)),
        Assert(Gtxn[2].xfer_asset() == tmpl_funds_asset_id), 
        Assert(Gtxn[2].asset_receiver() == tmpl_app_escrow_address),

        # investor opts-in to shares 
        Assert(Gtxn[3].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[3].xfer_asset() == tmpl_shares_asset_id),
        Assert(Gtxn[3].asset_amount() == Int(0)),
        Assert(Gtxn[3].asset_receiver() == Gtxn[3].sender()), # TODO is this optin check needed - if yes add it to other optins

        # the investor sends 3 txs (app call, pay for shares, shares optin)
        Assert(Gtxn[0].sender() == Gtxn[2].sender()),
        Assert(Gtxn[2].sender() == Gtxn[3].sender()),
        # TODO check that gtxn 1 sender is invest escrow and receiver app escrow?
        Assert(Gtxn[2].asset_amount() == Mul(Gtxn[1].asset_amount(), tmpl_share_price)), # Paying the correct price for the bought shares

        Approve()
    )

    program = Cond(
        [Global.group_size() == Int(7), handle_setup_dao],
        [Gtxn[0].application_args[0] == Bytes("invest"), handle_invest],
    )

    return compileTeal(program, Mode.Signature, version=5)

path = 'teal_template/investing_escrow.teal'
with open(path, 'w') as f:
    output = program()
    # print(output)
    f.write(output)
    print("Done! Wrote investing escrow TEAL to: " + path)