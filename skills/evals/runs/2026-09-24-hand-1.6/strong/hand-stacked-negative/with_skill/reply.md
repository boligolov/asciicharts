I drew this by hand, since no renderer was available. Every bar length was worked out from the numbers, not estimated. One cell is $2k on both sides of the zero line `¦`.

```
Monthly cash flow, $k (net at the end of each row)

Jan │    ▒▒▒▒¦████████████████████▓▓▓▓▓▓▓▓        47
Feb │     ▒▒▒¦███████████████████████▓▓▓▓▓▓       53
Mar │ ▒▒▒▒▒▒▒¦██████████████████████████▓▓▓▓▓▓▓▓▓ 56
Apr │     ▒▒▒¦█████████████████████████▓▓▓▓▓▓▓▓▓▓ 64

█ Subscriptions   ▓ Services   ▒ Refunds (negative)
```

| month | subscriptions | services | refunds | net |
|---|---|---|---|---|
| Jan | 40 (20 cells) | 15 (8) | −8 (4) | 47 |
| Feb | 46 (23) | 12 (6) | −5 (3) | 53 |
| Mar | 52 (26) | 18 (9) | −14 (7) | 56 |
| Apr | 49 (25) | 21 (10) | −6 (3) | 64 |

Net cash flow went up every month, from $47k to $64k. March had the most gross income ($70k), but its $14k of refunds, the largest of the four months, took the net down to $56k. April had the same $70k gross with only $6k refunded, which made it the best month.

How I scaled it: the widest positive stack is 70 and the deepest refund is 14, so 42 cells split 35 to the right and 7 to the left. That gives 0.5 cells per $1k on both sides. Where a stack didn't divide evenly, I split its cells by largest remainder so the segments add up exactly to the stack's rounded total. Jan: 20.36 + 7.64 comes out as 20 + 8. Apr: 24.5 + 10.5 is a tie, and ties go to the first series, so 25 + 10.
