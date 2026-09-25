```
Daily active users (thousands), last 14 days

   64 ┤                                ●                    
60.82 ┤                               · ··         ●        
57.64 ┤                              ·    ·●·    ·· ·       
54.45 ┤                             ·        ··●·    ·      
51.27 ┤                            ●                  ·   ● 
48.09 ┤                          ··                    ●··  
44.91 ┤            ●           ●·                           
41.73 ┤   ·●      · ··        ·                             
38.55 ┤●··  ··  ··    ·●     ·                              
35.36 ┤       ·●        ·    ·                              
32.18 ┤                  ·· ·                               
   29 ┤                    ●                                
       d1  d2  d3  d4  d5  d6  d7  d8  d9 d10 d11 d12 d13 d14
       38  41  36  44  40  29  45  52  64  57  55  61  48  50
```

Each `●` is one day's value and `·` joins them. The value axis runs from the lowest to the highest day (29 to 64 thousand), not from zero. Each row is about 3.2k apart, so the exact numbers are printed under the day labels. Daily users held around 36–45k for the first week, dropped to the low of 29k on d6, then climbed to a peak of 64k on d9. They stayed high at 55–61k through d12 and eased back to about 50k by d14.

I drew this by hand, without a renderer, using the asciicharts line-chart recipe. Every point's row was calculated from its value, not placed by eye. The chart is 12 rows tall, which is bigger than the recipe's comfortable limit for hand drawing, so check it against the printed values if a spot looks off.
