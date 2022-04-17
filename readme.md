Involved assets:

1) Funds asset: An ASA specified when creating the DAO in which the funds will be managed. Expected to be a stable coin normally.
2) DAO shares: An ASA that represents DAO shares, locking shares entitles investors to a proportional share of the DAO's income (more exactly a share of a funds % dedicated to investors, defined by the DAO owner).
3) \$CAPI: Works similarly to the DAO shares, but for the whole platform: locking \$CAPI entitles the holders to a % of the platform's fees.

# DAO contracts

## dao_app_approval

Contains the DAO's state. 

Notes:
- When investors lock shares, the "already claimed" local state is set to how much they'd be entitled based on their current holdings. This way they can claim dividend only for future income.
- Unlocking shares opts out investors from the app. Partial unlocking is not possible (all the shares have to be unlocked). Partial locking is possible (the locked shares are incremented).

## Dao escrow

Holds the DAO's funds. Flows:
1) Drain: retrieves the funds from customer_escrow. This is necessary to set the DAO's `GLOBAL_RECEIVED_TOTAL` global state, used to calculate the claimable dividend for the investors. Anyone can trigger this. This flow also sends the Capi fee ("global dividend") to capi_escrow.

2) Investing: When users buy shares, the payment (xfer) goes to this escrow.

3) Withdrawing: The DAO owner withdraws funds (e.g. to pay for company's expenses). The DAO owner can withdraw all the funds, emptying the escrow and preventing investors from claiming their dividend. This is intended, for now.

## customer_escrow

This is where DAO's customers send payments. It can only send funds to the DAO's escrow.

## investing_escrow

Contains the logic to sell shares (swap shares with funds asset). The DAO owner sends the shares here when creating the project. Checks that the correct funds amount is sent to the DAO's escrow.

Not sure that this should be a contract account. Maybe a delegated lsig is better.

It may also be possible to merge this with the DAO's escrow, now sure that a separate escrow is necessary.

## locking_escrow

The investors lock shares here to be entitled to the dividend.

# Capi contracts

## capi_app_approval

Analogous to dao_app_approval but for $capi holders and the global dividend.

## capi_escrow

Collects the platform's fees / dividend for $capi holders.
