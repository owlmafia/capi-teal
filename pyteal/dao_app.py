from pyteal import *
from common.app_call_checks import *
from common.asset_checks import *
from common.constants import *
from common.payments import *
from common.inner_txs import *
from common.state import *
from domain.setup_dao import *
from domain.update_dao import *
from domain.lock import *
from domain.investor_optin import *
from common.general import *
from domain.claim import *

"""App central approval"""

def approval_program():
    handle_create = Seq(
        Approve()
    )

    handle_update = Seq(
        is_group_size(1),

        is_app_call_by_creator(Gtxn[0]),

        Approve()
    )

    handle_setup_dao = Seq(
        # creator sends min balance to app address
        is_payment_to_this_app(Gtxn[0]),

        # app call
        is_app_call_noop_this_app_by_creator(Gtxn[1]),
        Assert(Or(
            is_args_length_res(Gtxn[1], 15),
            is_args_length_res(Gtxn[1], 16),
        )),

        # creator transfers shares (to be sold to investors) to app escrow
        is_asset_transfer(Gtxn[2]),
        # the asset transferred is what will be stored as shares asset id
        Assert(Gtxn[2].xfer_asset() == Btoi(Gtxn[1].application_args[0])),

        dao_setup_init_global_state(Gtxn[1].application_args),

        # checks depending on global state

        Assert(Gtxn[2].xfer_asset() == get_gs(GLOBAL_SHARES_ASSET_ID)),

        # creator's account setup

        setup_dao_optins(
            get_gs(GLOBAL_FUNDS_ASSET_ID),
            get_gs(GLOBAL_SHARES_ASSET_ID)
        ),

        Approve()
    )

    def handle_update_data_tx(tx):
        return Seq(
            is_app_call_noop_this_app_by_creator(tx),
            dao_update_set_state(tx.application_args)
        )

    handle_update_data_basic = Seq(
        handle_update_data_tx(Gtxn[0]),
        # handle_update_data_common,

        is_group_size(1),

        is_args_length(Gtxn[0], 9),

        Approve()
    )

    handle_update_data_with_image = Seq(
        handle_update_data_tx(Gtxn[1]),

        # group size checked in cond

        # increase min balance to hold new nft
        is_payment_to_this_app(Gtxn[0]),

        # the first tx is the payment to increase min balance, to be able to hold an additional asset
        Assert(Gtxn[1].application_args[0] == Bytes("update_data")),
        is_args_length(Gtxn[1], 10),

        If(get_gs(GLOBAL_IMAGE_URL) != Gtxn[1].application_args[9])
            .Then(setup_image_nft(Gtxn[1].application_args[9])),

        Approve()
    )

    handle_optin = Seq(
        is_group_size(1),

        is_this_app_call(Gtxn[0]),
        Assert(Gtxn[0].on_completion() == OnComplete.OptIn),

        investor_optin_init_state(),

        Approve()
    )

    handle_unlock = Seq(
        is_group_size(1),

        # app call to opt-out
        is_this_app_call(Gtxn[0]),
        Assert(Gtxn[0].on_completion() == OnComplete.CloseOut),

        # shares xfer to the investor
        send_asset(
            Gtxn[0].sender(), 
            get_gs(GLOBAL_SHARES_ASSET_ID), 
            get_ls(Gtxn[0].sender(), LOCAL_SHARES)
        ),


        # note: latest_timestamp doesn't work on dev mode! (e.g. currently is returning a date 5 days ago)
        # Log(Itob(Global.latest_timestamp())),
        
        # Don't allow to unlock until fund raising period ended.
        # We need this to be able to set a max limit to shares that can be bought
        # (that is, during the funds raising period, 
        # it's still unclear, for legal and UX reasons, what to do in the time after, including whether it should be possible to invest at all (currently it is)).
        # If the investor can't unlock, we can check the total shares in local state to prevent buying.
        # If the investor were to be able to unlock, we wouldn't have anything to add to
        # (note that asset balance doesn't work either, as after unlocking the user can transfer the shares to another account).
        Assert(Global.latest_timestamp() > get_gs(GLOBAL_TARGET_END_DATE)),        

        # TODO where is locked shares local state decremented? not tested?

        # decrement locked shares global state
        decrement_gs(GLOBAL_LOCKED_SHARES, get_ls(Gtxn[0].sender(), LOCAL_SHARES)),

        Approve()
    )

    handle_claim_claimable_dividend = ScratchVar(TealType.uint64)
    handle_claim = Seq(
        is_group_size(1),

        # app call
        is_this_noop_app_call(Gtxn[0]),

        handle_claim_claimable_dividend.store(calc_claimable_dividend(Gtxn[0].sender())),
        
        #TODO tests: can't withdraw and claim more than available amount

        # has to be <= available amount
        Assert(handle_claim_claimable_dividend.load() <= get_gs(GLOBAL_AVAILABLE_AMOUNT)),

        # send dividend to caller
        send_asset_no_set_fee(
            Gtxn[0].sender(), 
            get_gs(GLOBAL_FUNDS_ASSET_ID), 
            handle_claim_claimable_dividend.load()
        ),

        # decrease available amount
        # no underflow possible, since we checked that claimable_dividend <= GLOBAL_AVAILABLE_AMOUNT
        # NOTE: BEFORE updating LOCAL_CLAIMED_TOTAL, since we read it to calculate the current divident being claimed
        # (TODO above solved by using scratch?)
        decrement_gs(GLOBAL_AVAILABLE_AMOUNT, handle_claim_claimable_dividend.load()),

        # update local state with retrieved dividend
        increment_ls(
            Gtxn[0].sender(), 
            LOCAL_CLAIMED_TOTAL,
            handle_claim_claimable_dividend.load()
        ),

        Approve()
    )

    # expects tx 1 to be the shares xfer to the app and its sender verified as app caller (local state)
    @Subroutine(TealType.none)
    def lock_shares(share_amount, sender):
        claimable_before_locking = ScratchVar(TealType.uint64)

        return Seq(
            claimable_before_locking.store(calc_claimable_dividend(Gtxn[0].sender())),

            # set / increment share count in local state 
            increment_ls(sender, LOCAL_SHARES, share_amount),

            # initialize already claimed local state
            set_ls(
                sender,
                LOCAL_CLAIMED_TOTAL,
                Minus(calc_claimable_dividend(Gtxn[0].sender()), claimable_before_locking.load())
            ),
            
            # remember initial already claimed local state
            set_ls(
                sender,
                LOCAL_CLAIMED_INIT,
                get_ls(sender, LOCAL_CLAIMED_TOTAL)
            ),

            # increment locked shares global state
            increment_gs(GLOBAL_LOCKED_SHARES, share_amount)
        )

    handle_lock = Seq(
        # app call to update state
        is_this_noop_app_call(Gtxn[0]),
        is_args_length(Gtxn[0], 4),

        # shares xfer to app
        is_shares_transfer_to_this_app(Gtxn[1]),
        Assert(Gtxn[1].asset_amount() > Int(0)),

        # app caller is locking the shares
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),

        # save shares on local state
        lock_shares(Gtxn[1].asset_amount(), Gtxn[0].sender()),

        # save acked prospectus
        save_prospectus(Gtxn[0].sender(), Gtxn[0].application_args, 1),

        Approve()
    )

    app_escrow_funds_balance = AssetHolding.balance(
        Global.current_application_address(), get_gs(GLOBAL_FUNDS_ASSET_ID)
    )

    # funds that are on the app's balance but haven't been drained (made available) yet
    # note that withdrawals don't affect this value, 
    # as they're substracted atomically (in the withdrawal group) from both balance and GLOBAL_AVAILABLE_AMOUNT
    # so basic arithmetic: if we substract a value from both operands of a substraction, the result is unaffected
    handle_drain_not_yet_drained_amount = Minus(
        app_escrow_funds_balance.value(),
        get_gs(GLOBAL_AVAILABLE_AMOUNT)
    )

    def calculate_capi_fee(amount): 
        return Div(
            Mul(
                Mul(amount, tmpl_precision),
                tmpl_capi_share
            ),
            tmpl_precision_square
        )

    # handle_drain_capi_fee = ScratchVar(TealType.uint64)
    handle_drain = Seq(
        # handle_drain_capi_fee.store(calculate_capi_fee(handle_drain_not_yet_drained_amount)),
        
        is_group_size(1),

        # app call
        is_this_noop_app_call(Gtxn[0]),

        # needs to be listed like this, see: https://forum.algorand.org/t/using-global-get-ex-on-noop-call-giving-error-when-deploying-app/5314/2
        # (app_escrow_funds_balance is used in handle_drain_not_yet_drained_amount)
        app_escrow_funds_balance,

        # increment total received
        increment_gs(
            GLOBAL_RECEIVED_TOTAL,
            Minus(handle_drain_not_yet_drained_amount, calculate_capi_fee(handle_drain_not_yet_drained_amount))
        ),

        # pay capi fee
        # note BEFORE updating GLOBAL_AVAILABLE_AMOUNT as it needs this state 
        # to calculate not yet drained amount  
        send_asset_no_set_fee(
            tmpl_capi_escrow_address,
            get_gs(GLOBAL_FUNDS_ASSET_ID), 
            calculate_capi_fee(handle_drain_not_yet_drained_amount)
        ),

        # increment available amount
        # WA = WA + NYD (not yet drained) - fee on NYD
        # in words: by draining we make the "new income" (in prev. implementation, customer escrow balance) minus capi fee available to be withdrawn
        # note AFTER the inner tx, 
        # which accesses GLOBAL_AVAILABLE_AMOUNT to calculate the not yet drained amount / the capi fee
        increment_gs(
            GLOBAL_AVAILABLE_AMOUNT, 
            Minus(handle_drain_not_yet_drained_amount, calculate_capi_fee(handle_drain_not_yet_drained_amount))
        ),

        Approve()
    )

    app_shares_balance = AssetHolding.balance(
        Global.current_application_address(), get_gs(GLOBAL_SHARES_ASSET_ID)
    )

    handle_invest_calculated_share_amount = ScratchVar(TealType.uint64)
    # note that when investing (opposed to locking, where there's a shares xfer), 
    # the share amount is calculated here (based on sent funds and share price)
    handle_invest = Seq(
        # is_group_size(3), # used as condition

        # investor opts-in to shares (needs to be before app call with inner tx sending the asset)
        # optin to shares
        is_shares_transfer(Gtxn[0]),
        Assert(Gtxn[0].asset_amount() == Int(0)),
        Assert(Gtxn[0].asset_receiver() == Gtxn[0].sender()),

        # app call to initialize shares state
        is_this_noop_app_call(Gtxn[1]),
        is_args_length(Gtxn[1], 5),

        # investor pays for shares: funds xfer to app escrow
        is_funds_transfer_to_this_app(Gtxn[2]),
        Assert(Gtxn[2].asset_amount() > Int(0)),

        # increment available amount state
        # investments don't pay capi fee or generate dividend, so are immediately available (don't have to be drained)
        increment_gs(GLOBAL_AVAILABLE_AMOUNT, Gtxn[2].asset_amount()),

        # the investor sends all txs
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),
        Assert(Gtxn[1].sender() == Gtxn[2].sender()),

        # save the calculated share amount in scratch (used in multiple places)
        handle_invest_calculated_share_amount.store(Div(Gtxn[2].asset_amount(), tmpl_share_price)),

        # double-check that the share amount matches what the caller expects
        # (just in case for unexpected rounding issues)
        Assert(handle_invest_calculated_share_amount.load() == Btoi(Gtxn[1].application_args[1])),

        # sanity check: the bought share amount is > 0 (even if for whatever reason 0 was passed as expected/argument)
        Assert(handle_invest_calculated_share_amount.load() > Int(0)),

        # needs to be listed like this, see: https://forum.algorand.org/t/using-global-get-ex-on-noop-call-giving-error-when-deploying-app/5314/2
        # (app_escrow_funds_balance is used in handle_drain_not_yet_drained_amount)
        app_shares_balance,

        # the bought share amount is <= shares for sale (balance - locked -> not locked, i.e. available for sale)
        Assert(handle_invest_calculated_share_amount.load() <= Minus(
            app_shares_balance.value(),
            get_gs(GLOBAL_LOCKED_SHARES)
        )),

        # update total raised amount
        increment_gs(GLOBAL_RAISED, Gtxn[2].asset_amount()),

        # total raised is below or equal to max allowed amount (regulatory)
        Assert(handle_invest_calculated_share_amount.load() <= tmpl_max_raisable_amount),

        # is investing more than min amount (share amount)
        Assert(handle_invest_calculated_share_amount.load() >= get_gs(GLOBAL_MIN_INVEST_AMOUNT)),

        # save shares on local state
        lock_shares(
            handle_invest_calculated_share_amount.load(),
            Gtxn[0].sender()
        ),

        # has invested (is investing + possibly has invested before) less or same than max amount (share amount) 
        # NOTE this check has to be AFTER lock_shares, as it expects LOCAL_SHARES to be incremented (by invested amount)
        Assert(get_ls(Gtxn[0].sender(), LOCAL_SHARES) <= get_gs(GLOBAL_MAX_INVEST_AMOUNT)),

        # save acked prospectus
        save_prospectus(Gtxn[0].sender(), Gtxn[1].application_args, 2),

        Approve()
    )

    handle_withdrawal = Seq(
        is_group_size(1),

        # only the owner can withdraw
        Assert(Gtxn[0].sender() == Global.creator_address()),

        # has to be after min target end date
        Assert(Global.latest_timestamp() > get_gs(GLOBAL_TARGET_END_DATE)),

        # has to be <= available amount
        Assert(Btoi(Gtxn[0].application_args[1]) <= get_gs(GLOBAL_AVAILABLE_AMOUNT)),

        # the min target was met
        # (if the target wasn't met, the project can't start and investors can reclaim their money)
        Assert(get_gs(GLOBAL_RAISED) >= get_gs(GLOBAL_TARGET)),

        # decrease available amount
        set_gs(GLOBAL_AVAILABLE_AMOUNT, Minus(
            get_gs(GLOBAL_AVAILABLE_AMOUNT),
            Btoi(Gtxn[0].application_args[1])
        )),

        # send the funds to the withdrawer
        send_asset_no_set_fee(
            Gtxn[0].sender(),
            get_gs(GLOBAL_FUNDS_ASSET_ID),
            Btoi(Gtxn[0].application_args[1])
        ),

        Approve()
    )

    # development / testing settings
    handle_dev_settings = Seq(
        is_group_size(1),
        is_args_length(Gtxn[0], 2),

        # allow to set raising end date on the fly, to test reaching this date without having to wait
        set_gs(GLOBAL_TARGET_END_DATE, Btoi(Gtxn[0].application_args[1])),

        Approve()
    )

    handle_team = Seq(
        is_group_size(1),
        is_args_length(Gtxn[0], 2),

        # only the owner set team
        Assert(Gtxn[0].sender() == Global.creator_address()),

        set_gs(GLOBAL_TEAM_URL, Gtxn[0].application_args[1]),

        Approve()
    )

    # allow the investors to get their investments back if the funding target wasn't met
    #
    # note that for reclaim, we expect the user to have unlocked the shares
    # there's no direct path from locked shares to reclaiming in teal - the app can chain these steps
    handle_reclaim = Seq(
        # app call
        is_this_noop_app_call(Gtxn[0]),

        # shares being sent back
        is_shares_transfer_to_this_app(Gtxn[1]),
        Assert(Gtxn[1].asset_amount() > Int(0)),
        Assert(Gtxn[1].sender() == Gtxn[0].sender()),

        # reclaiming after min target end date
        Assert(Global.latest_timestamp() > get_gs(GLOBAL_TARGET_END_DATE)),

        # min target wasn't met
        Assert(
            # NOTE that raised funds currently means only investments.
            # regular payments (which could be donations) sent to the app's escrow or the customer escrow are ignored here
            # (the UI doesn't support donations (yet?), but they're of course technically possible)
            get_gs(GLOBAL_RAISED) < get_gs(GLOBAL_TARGET)
        ),

        # send paid funds back
        send_asset_no_set_fee(
            Gtxn[0].sender(),
            get_gs(GLOBAL_FUNDS_ASSET_ID),
            # TODO scratch?
            Gtxn[1].asset_amount() * get_gs(GLOBAL_SHARE_PRICE),
        ),

        # decrease available amount
        set_gs(GLOBAL_AVAILABLE_AMOUNT, Minus(
            get_gs(GLOBAL_AVAILABLE_AMOUNT),
            Gtxn[1].asset_amount() * get_gs(GLOBAL_SHARE_PRICE)
        )),

        Approve()
    )

    program = Cond(
        [And(
            Gtxn[0].type_enum() == TxnType.AssetTransfer,
            Global.group_size() == Int(3)
        ), handle_invest],
        [Global.group_size() == Int(3), handle_setup_dao],
        [Gtxn[0].on_completion() == Int(4), handle_update],
        [And(
            # app call to differentiate from update, where first tx is a payment
            # TODO how do we make is_app_call usable both here and in the other (embedded in Seq) expressions?,
            Gtxn[0].type_enum() == TxnType.ApplicationCall, 
            Gtxn[0].application_id() == Int(0)
        ), handle_create],
        [Global.group_size() == Int(2), Cond(
            [Gtxn[0].type_enum() == TxnType.Payment, handle_update_data_with_image],
            [Gtxn[0].application_args[0] == Bytes("lock"), handle_lock],
            [Gtxn[0].application_args[0] == Bytes("reclaim"), handle_reclaim],
        )],
        [Gtxn[0].application_args[0] == Bytes("optin"), handle_optin],
        [Gtxn[0].application_args[0] == Bytes("unlock"), handle_unlock],
        [Gtxn[0].application_args[0] == Bytes("claim"), handle_claim],
        [Gtxn[0].application_args[0] == Bytes("drain"), handle_drain],
        [Gtxn[0].application_args[0] == Bytes("update_data"), handle_update_data_basic],
        [Gtxn[0].application_args[0] == Bytes("withdraw"), handle_withdrawal],
        # [Gtxn[0].application_args[0] == Bytes("dev_settings"), handle_dev_settings],
        [Gtxn[0].application_args[0] == Bytes("team"), handle_team],
    )

    # program = Approve()

    return compileTeal(program, Mode.Application, version=6)


def clear_program():
    return compileTeal(Int(1), Mode.Application, version=6)


def export(path, output):
    with open(path, "w") as f:
        # print(output)
        f.write(output)
        print("Wrote TEAL to: " + path)


export("teal_template/dao_app_approval.teal", approval_program())
export("teal_template/dao_app_clear.teal", clear_program())

print("Done! Wrote dao approval and clear TEAL")
