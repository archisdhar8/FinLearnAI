// Complete module content with quizzes and interactive elements
// Extracted from quantcademy-app/pages/learning_modules.py

export interface QuizQuestion {
  question: string;
  options: string[];
  correct: number;
  explanation?: string;
}

export interface ToolLink {
  text: string;
  route: string;
  description: string;
}

export interface Lesson {
  id: string;
  title: string;
  content: string;
  quiz?: QuizQuestion[];
  interactiveElements?: string[]; // Component names to render
  toolLinks?: ToolLink[]; // Links to AI tools
  goalReminder?: string; // Goal reminder at end of lesson
}

export interface Module {
  id: string;
  title: string;
  description: string;
  level: 'Beginner' | 'Intermediate' | 'Advanced';
  goal: string; // Module goal statement
  lessons: Lesson[];
  finalQuiz: QuizQuestion[];
}

export const MODULES: Record<string, Module> = {
  "foundations": {
    id: "foundations",
    title: "The Foundation",
    description: "Core concepts every first-time investor should know.",
    level: "Beginner",
    goal: "Understand investing well enough to confidently open an account and make your first investment.",
    lessons: [
      {
        id: "what_is_investing",
        title: "What is Investing?",
        goalReminder: "You now understand WHY investing matters. Next up: what you can actually buy.",
        toolLinks: [
          {
            text: "See Your Money Grow (or Shrink)",
            route: "/simulator",
            description: "Try the Portfolio Simulator NOW. Set monthly investment to $200, years to 30, and watch what happens. Then try $0/month and see the difference. This is YOUR future."
          }
        ],
        content: `
> **Before you read another word:** Go to the Portfolio Simulator below. Put in $200/month, 30 years, 7% return. See that number? That could be YOUR retirement. Now change it to $0/month. See the difference? That's what waiting costs you.

---

## What Is Investing, Really?

**Investing = using your money to make more money over time.**

That's it. You're not gambling. You're not day trading. You're buying pieces of real companies and letting them grow.

- **$100 under your mattress** → Still $100 in 10 years
- **$100 invested at 7%/year** → About $200 in 10 years

Your money works while you sleep.

---

> 💡 **QUICK STAT:** If you invested $1,000 in the S&P 500 in 2014, you'd have ~$3,500 today. That's doing nothing but waiting.

---

## The Savings Account Trap

Here's the uncomfortable truth: **keeping all your money in savings is risky.**

Not "lose it all" risky. But "guaranteed to lose value" risky.

**Inflation** = stuff costs more every year.
- Milk that cost $3 last year → $3.10 this year
- Your $100 buys less stuff, even though it's still $100

At 3% inflation, $100 today = **$74 in purchasing power** after 10 years.

You didn't lose the money. You lost what the money can buy.

---

> 📊 **TRY IT:** Use the Inflation Calculator below. Enter $10,000 and see what it's worth in 20 years if you don't invest.

---

## Saving vs Investing: The Simple Rule

| | Saving | Investing |
|---|---|---|
| **For** | Emergencies, short-term | Retirement, 5+ year goals |
| **Risk** | Low (but loses to inflation) | Higher (but beats inflation) |
| **Timeline** | Need it in 1-2 years | Don't need it for 5+ years |

**The key difference? Time.**

Need money soon → savings account.
Don't need it for years → invest it.

---

## Why Starting NOW Matters

> 🎯 **THE MATH THAT CHANGES EVERYTHING:**
>
> **Start at 25:** Invest $200/month → **$500,000+ by 65**
>
> **Start at 35:** Need $450/month to catch up
>
> **Start at 45:** Need $1,000/month to catch up

Same destination. But waiting 10 years means paying **2x more** to get there.

---

> ✅ **MILESTONE COMPLETE:** You now understand more about investing than most Americans. Seriously. Most people never learn this.

---

## Your Action Item

Before moving on, go to the **Portfolio Simulator** and try these:
1. **Your realistic scenario:** Your age, $200/month, 30 years
2. **The "I'll start later" scenario:** Same but 10 fewer years
3. **The "I wish I started earlier" scenario:** Add 10 more years

See the difference? That's why we're here.
        `,
        interactiveElements: ['InflationCalculator', 'CompoundCalculator'],
        quiz: [
          {
            question: "What's the main difference between saving and investing?",
            options: [
              "Saving is riskier than investing",
              "Investing is for long-term goals, saving is for short-term needs",
              "They're the same thing",
              "Only rich people can invest"
            ],
            correct: 1,
            explanation: "Investing is for money you won't need for years, while saving is for emergencies and short-term goals."
          },
          {
            question: "Why does starting to invest early matter so much?",
            options: [
              "You have more money when you're young",
              "Time allows compound interest to work its magic",
              "Stocks always go up when you're young",
              "It doesn't really matter"
            ],
            correct: 1,
            explanation: "Starting early gives your money more time to compound, which can double or triple your returns over decades."
          }
        ]
      },
      {
        id: "what_youre_buying",
        title: "What You're Actually Buying",
        goalReminder: "You now know the 3 main investment types. Most beginners just need index funds. Keep going!",
        toolLinks: [
          {
            text: "See Real Stocks RIGHT NOW",
            route: "/screener",
            description: "Go look at AAPL, MSFT, GOOGL in our Stock Screener. These are real companies you could own a piece of TODAY. See their current prices, trends, and AI analysis."
          }
        ],
        content: `
> **Quick challenge:** After this lesson, go to the Stock Screener and find Apple (AAPL). Look at its current price. That's how much ONE share costs. You could own a piece of a $3 trillion company for that price.

---

## The 3 Things You Can Buy

| Type | What It Is | Risk | Return |
|------|-----------|------|--------|
| **Stocks** | Own a piece of a company | Higher | ~10%/year historically |
| **Bonds** | Lend money, get interest | Lower | ~4-5%/year |
| **Funds** | Basket of stocks/bonds | Medium | Depends on mix |

That's it. Everything else is a variation of these three.

---

## Stocks: You Own Part of the Company

**Buy 1 share of Apple = you own a tiny piece of Apple Inc.**

What that means:
- Apple profits → you might get **dividends** (cash payments)
- Apple grows → your shares are worth more
- Apple tanks → your shares lose value

> 💡 **REAL EXAMPLE:** 1 share of Apple in 2010 = ~$10. Today = ~$180. That's 18x your money in 14 years.

Stocks are "riskier" because prices bounce around daily. But over decades? They've beaten everything else.

---

## Bonds: You're the Bank

**Buy a bond = you're lending money and getting paid interest.**

Example: You give the government $1,000. They say:
- "We'll pay you 4% interest every year"
- "In 10 years, we'll give your $1,000 back"

Safer than stocks. But lower returns. Most young investors don't need many bonds yet.

---

## Funds: The Easy Button

**Don't want to pick individual stocks? Buy a fund that holds hundreds of them.**

| Fund Type | What It Does | Cost |
|-----------|-------------|------|
| **Index Fund** | Tracks S&P 500 (top 500 companies) | Very low (~0.03%) |
| **ETF** | Same as index fund, trades like a stock | Very low |
| **Mutual Fund** | Manager picks stocks for you | Higher (1-2%) |

> 🎯 **THE BEGINNER ANSWER:** Just buy an S&P 500 index fund (like VOO, SPY, or FXAIX). You instantly own a piece of Apple, Microsoft, Google, Amazon, and 496 other companies.

---

> ✅ **MILESTONE:** You now know more about investment types than most adults. Index funds are the answer for 90% of beginners. Don't overthink it.

---

## Your Action Item

Go to the **Stock Screener** and:
1. Look up **AAPL** (Apple) - see the current price
2. Look up **SPY** (S&P 500 ETF) - this is 500 companies in one
3. Compare the AI signals - which looks more stable?

This is real. These are things you can actually buy.
        `,
        quiz: [
          {
            question: "When you buy a stock, what are you actually buying?",
            options: [
              "A loan to a company",
              "A small ownership stake in a company",
              "A guarantee of future profits",
              "A government bond"
            ],
            correct: 1,
            explanation: "Stocks represent partial ownership of a company. You become a shareholder."
          },
          {
            question: "What's the main advantage of index funds for beginners?",
            options: [
              "They guarantee profits",
              "They're managed by experts who pick winners",
              "They provide instant diversification at low cost",
              "They have no risk"
            ],
            correct: 2,
            explanation: "Index funds give you exposure to hundreds of companies at once, reducing risk through diversification."
          }
        ]
      },
      {
        id: "how_markets_work",
        title: "How Markets Function",
        goalReminder: "You now understand how prices move. This knowledge will keep you calm when markets get crazy.",
        toolLinks: [
          {
            text: "See Charts in Action",
            route: "/analyzer",
            description: "Upload any stock chart to our Chart Analyzer. Watch AI identify support levels (where prices tend to stop falling) and resistance levels (where they stop rising)."
          },
          {
            text: "Watch Real Price Movement",
            route: "/screener",
            description: "Go to Stock Screener and watch the trends. Green = uptrend. Red = downtrend. This is supply and demand in action."
          }
        ],
        content: `
> **The secret:** The stock market isn't mysterious. It's just people buying and selling. That's it.

---

## How Prices Actually Work

**More buyers than sellers → price goes UP**
**More sellers than buyers → price goes DOWN**

That's literally it. Everything else (earnings reports, Fed announcements, analyst ratings) just affects how many people want to buy or sell.

---

> 📊 **TRY IT:** Go to the Stock Screener and look at any stock's trend. Uptrend = more buyers lately. Downtrend = more sellers. You're watching supply and demand in real-time.

---

## The Basics You Need to Know

| What | Details |
|------|---------|
| **Where** | NYSE, NASDAQ (stock exchanges) |
| **When** | 9:30 AM - 4:00 PM Eastern, Mon-Fri |
| **How** | You buy from sellers, sell to buyers |

When you click "buy" on your brokerage app, someone else clicked "sell" at that exact moment. You're trading with real people.

---

## What Makes Prices Move?

| Factor | Effect |
|--------|--------|
| **Good earnings** | Stock usually goes up |
| **Bad news/scandal** | Stock usually goes down |
| **Fed raises rates** | Market often drops |
| **Fear/panic** | Everything drops |
| **Optimism/hype** | Everything rises |

> 💡 **KEY INSIGHT:** Short-term = emotions and news. Long-term = actual business performance. This is why we don't panic sell.

---

## The Good News: You Don't Need to Predict Anything

Most successful investors:
- Buy regularly (every paycheck)
- Hold for years/decades
- Don't try to time the market
- Ignore daily news

That's it. No crystal ball needed.

---

> ✅ **MILESTONE:** You now understand markets better than people who watch CNBC all day. They're trying to predict. You're just going to buy and hold.
        `,
        quiz: [
          {
            question: "What primarily determines stock prices?",
            options: [
              "The government sets prices",
              "Supply and demand from buyers and sellers",
              "The company's CEO decides",
              "Random chance"
            ],
            correct: 1,
            explanation: "Stock prices are determined by supply and demand - more buyers push prices up, more sellers push prices down."
          }
        ]
      },
      {
        id: "time_and_compounding",
        title: "Time and Compounding",
        goalReminder: "You now understand the most powerful force in investing. Time is on your side - if you start now.",
        toolLinks: [
          {
            text: "Watch Compounding in Action",
            route: "/simulator",
            description: "Go to Portfolio Simulator. Set $200/month for 40 years. Now change to 30 years. See how much that 10 years costs you? That's compounding."
          }
        ],
        content: `
> **This is the most important lesson.** Compounding is why starting NOW matters more than how much you invest.

---

## The Magic of Compounding (In 30 Seconds)

**Year 1:** Invest $1,000, earn 10% = **$1,100**
**Year 2:** Earn 10% on $1,100 = **$1,210**
**Year 3:** Earn 10% on $1,210 = **$1,331**

See it? Each year you earn more because you're earning on your earnings. This snowballs over decades.

---

> 📊 **TRY IT NOW:** Use the Compound Calculator below. Put in $10,000, 7% return, 30 years. That's ~$76,000. Now try 40 years. That's ~$150,000. Ten extra years = DOUBLE the money.

---

## The Rule of 72 (Memorize This)

**72 ÷ your return rate = years to double your money**

| Return | Years to Double |
|--------|-----------------|
| 6% | 12 years |
| 7% | ~10 years |
| 10% | ~7 years |

At 7% (stock market average), your money doubles every 10 years.
- Age 25: $10,000
- Age 35: $20,000
- Age 45: $40,000
- Age 55: $80,000
- Age 65: $160,000

**One investment. No extra contributions. Just time.**

---

## The Story That Will Change How You Think

> 🎯 **SARAH vs MIKE:**
>
> **Sarah:** Invests $200/month from age 25-35, then STOPS (10 years, $24,000 total)
>
> **Mike:** Invests $200/month from age 35-65 (30 years, $72,000 total)
>
> **At age 65, they have the SAME amount: ~$240,000**

Sarah invested 1/3 the money but got the same result. The only difference? She started 10 years earlier.

---

> ✅ **MILESTONE:** You now understand why every financial advisor says "start early." It's not a cliché - it's math. And the math is brutal if you wait.

---

## Your Action Item

Go to the **Portfolio Simulator** and run YOUR numbers:
1. Your current age
2. $200/month (or whatever you can do)
3. Retirement age 65

Now add 5 years to your starting age. See the difference? That's what waiting costs.
        `,
        interactiveElements: ['CompoundCalculator'],
        quiz: [
          {
            question: "Using the Rule of 72, how long does it take to double your money at 6% annual return?",
            options: [
              "6 years",
              "12 years",
              "18 years",
              "72 years"
            ],
            correct: 1,
            explanation: "72 ÷ 6 = 12 years. The Rule of 72 gives you a quick estimate of doubling time."
          },
          {
            question: "What makes compound interest so powerful?",
            options: [
              "You earn interest only on your original investment",
              "You earn interest on your interest, creating exponential growth",
              "The government adds extra money",
              "It only works for rich people"
            ],
            correct: 1,
            explanation: "Compound interest means your earnings generate their own earnings, leading to exponential growth over time."
          }
        ]
      },
      {
        id: "basics_of_risk",
        title: "The Basics of Risk",
        goalReminder: "You now understand that risk isn't scary - it's manageable. Diversify and don't panic. That's it.",
        toolLinks: [
          {
            text: "See Risk in Real Stocks",
            route: "/screener",
            description: "Compare individual stocks (TSLA, AAPL) to ETFs (SPY, QQQ) in the Stock Screener. Notice how ETFs have smoother trends? That's diversification reducing risk."
          }
        ],
        content: `
> **Risk doesn't mean "lose everything."** It means "how much your investments bounce around." And you can manage it.

---

## The Risk-Reward Tradeoff (No Free Lunch)

| Investment | Risk | Average Return |
|------------|------|----------------|
| Savings account | Very low | 0.5% |
| Bonds | Low | 3-5% |
| Stock index funds | Medium | 7-10% |
| Individual stocks | High | -100% to +1000% |

**Higher returns = higher risk. Always.** Anyone promising otherwise is lying.

---

## The 3 Types of Risk

| Risk | What It Is | Example |
|------|-----------|---------|
| **Market Risk** | Whole market drops | 2008, 2020 crashes |
| **Company Risk** | One company fails | Enron, Blockbuster |
| **Inflation Risk** | Cash loses value | Your savings account |

> 💡 **KEY INSIGHT:** Keeping all your money in cash feels safe but guarantees you lose to inflation. That's a risk too.

---

## How to Manage Risk (3 Rules)

**1. Diversify** - Own many investments, not just one
- Bad: All your money in Tesla
- Good: S&P 500 index fund (500 companies)

**2. Match risk to timeline**
- Need money in 1-2 years → savings/bonds
- Don't need it for 10+ years → mostly stocks

**3. Don't panic sell**
- Markets drop 20-30% sometimes. It's normal.
- Selling during a crash = locking in losses
- Staying invested = recovering when it bounces back

---

> 📊 **TRY IT:** Go to Stock Screener. Compare TSLA (individual stock) to SPY (500 companies). Look at the trend confidence. Which is more stable? That's diversification.

---

## Be Honest About Your Risk Tolerance

Can you watch your portfolio drop 30% and NOT sell?

- **Yes** → You can handle more stocks
- **No** → Add more bonds, sleep better

A boring portfolio you stick with beats an exciting one you panic-sell.

---

> ✅ **MILESTONE:** You now understand risk better than most investors. The secret? Diversify, match to timeline, don't panic. That's it.
        `,
        interactiveElements: ['RiskReturnChart'],
        quiz: [
          {
            question: "What does 'risk' mean in investing?",
            options: [
              "The chance of losing all your money",
              "How much your investments might go up or down in value",
              "The fees you pay",
              "How complicated the investment is"
            ],
            correct: 1,
            explanation: "Risk refers to volatility - how much the value of your investment fluctuates over time."
          },
          {
            question: "Why is diversification important?",
            options: [
              "It guarantees profits",
              "It reduces the impact of any single investment failing",
              "It makes investing more exciting",
              "It's required by law"
            ],
            correct: 1,
            explanation: "Diversification spreads your money across many investments, so one failure doesn't devastate your portfolio."
          }
        ]
      },
      {
        id: "accounts_and_setup",
        title: "Accounts and Setup",
        goalReminder: "You now know WHERE to invest. The next step is actually opening an account. You can do this TODAY.",
        content: `
> **This is where it gets real.** After this lesson, you'll know exactly which account to open first.

---

## Where to Actually Invest

**A brokerage account** = a bank account for investments

| Brokerage | Best For | Minimum |
|-----------|----------|---------|
| **Fidelity** | Beginners, great app | $0 |
| **Vanguard** | Index fund investors | $0 |
| **Schwab** | All-around solid | $0 |
| **Robinhood** | Simple UI, crypto | $0 |

All have $0 trading fees. Pick one with a good app. You can always switch later.

---

## The Account Priority Order

> 🎯 **FOLLOW THIS EXACT ORDER:**
>
> **1. 401(k) up to employer match** (if available) - This is FREE MONEY
>
> **2. Emergency fund** - 3-6 months expenses in savings
>
> **3. Roth IRA** - Tax-free growth, $7,000/year limit
>
> **4. Max 401(k)** - $23,000/year limit
>
> **5. Taxable brokerage** - No limits, no special tax benefits

---

## Retirement Accounts Explained (Simply)

| Account | Who Opens It | Tax Benefit | Catch |
|---------|-------------|-------------|-------|
| **401(k)** | Through employer | Pre-tax (save now) | Can't touch until 59½ |
| **Traditional IRA** | You | Pre-tax (save now) | Can't touch until 59½ |
| **Roth IRA** | You | Tax-free withdrawals later | Pay taxes now |

> 💡 **SIMPLE RULE:** If you're young and in a low tax bracket, Roth is usually better. Tax-free growth for decades is powerful.

---

## The Employer Match (Don't Miss This)

If your employer offers a 401(k) match, **this is the highest-return investment that exists.**

Example: Employer matches 50% up to 6% of salary
- You contribute 6% ($3,600 on $60k salary)
- Employer adds $1,800 FREE
- That's an instant 50% return before any market gains

**Always get the full match. Always.**

---

> ✅ **MILESTONE:** You now know exactly which accounts to open and in what order. Most people never figure this out. You just did.

---

## Your Action Item

**This week:** Open a Roth IRA at Fidelity, Vanguard, or Schwab. It takes 15 minutes. You don't have to fund it yet - just open it.
        `,
        quiz: [
          {
            question: "What's the first investment priority if your employer offers a 401(k) match?",
            options: [
              "Max out a Roth IRA first",
              "Contribute enough to get the full employer match",
              "Buy individual stocks",
              "Pay off all debt first"
            ],
            correct: 1,
            explanation: "An employer match is essentially free money - you should always capture the full match before other investments."
          }
        ]
      },
      {
        id: "first_time_mindset",
        title: "First Time Investor Mindset",
        goalReminder: "You've completed The Foundation! You now know more about investing than most Americans. Time to actually start.",
        toolLinks: [
          {
            text: "One Last Look at Your Future",
            route: "/simulator",
            description: "Before you finish this module, run the Portfolio Simulator one more time with YOUR numbers. That's your future if you start now."
          }
        ],
        content: `
> **The hardest part isn't the math.** It's your own brain. This lesson will save you from the mistakes that cost most investors money.

---

## The 4 Mistakes That Destroy Returns

| Mistake | Why It Happens | The Fix |
|---------|---------------|---------|
| **Waiting for the "right time"** | Fear of buying at the top | There's no perfect time. Start now. |
| **Checking too often** | Anxiety, FOMO | Check monthly, not daily |
| **Panic selling** | Market drops feel scary | Drops are sales. Stay invested. |
| **Chasing hot tips** | Greed, social pressure | Boring index funds win |

> 💡 **FACT:** The average investor earns ~4% when the market returns ~10%. Why? They buy high (excitement) and sell low (fear).

---

## The Mindset That Actually Works

**Think in decades, not days**
- You're building wealth over 30+ years
- A bad month is noise
- A bad year is noise
- Stay invested

**Automate everything**
- Set up auto-transfers from your paycheck
- You can't panic sell what you don't think about
- "Set it and forget it" beats active trading

**Ignore financial news**
- Headlines need drama for clicks
- "Markets do normal thing" isn't news
- Turn off CNBC

---

> 📊 **THE DATA:** From 1980-2020, if you missed just the 10 best days in the market, your returns dropped from 2,600% to 800%. Those best days often come right after the worst days. If you panic sold, you missed them.

---

## Your Investing Checklist

Before you leave this module, you should:

- [ ] Understand why investing beats saving (inflation)
- [ ] Know the difference between stocks, bonds, and funds
- [ ] Know that index funds are the answer for beginners
- [ ] Understand compounding and why starting early matters
- [ ] Know which account to open first
- [ ] Be ready to NOT panic when markets drop

---

> ✅ **MODULE COMPLETE:** You now know more about investing than 80% of Americans. Seriously. Most people never learn this stuff.
>
> **Your mission:** Open an account this week. Buy an S&P 500 index fund. Set up auto-invest. Then forget about it for 30 years.

---

## The Final Truth

Millions of regular people build wealth through investing. Not geniuses. Not finance majors. Regular people who:
1. Started
2. Stayed consistent
3. Didn't panic

That's it. You can do this.
        `,
        quiz: [
          {
            question: "What's the biggest mistake new investors make during market drops?",
            options: [
              "Buying more at lower prices",
              "Panic selling and locking in losses",
              "Staying invested",
              "Checking their portfolio"
            ],
            correct: 1,
            explanation: "Panic selling during drops locks in your losses and means you miss the recovery. Stay the course."
          },
          {
            question: "How often should long-term investors check their portfolio?",
            options: [
              "Multiple times per day",
              "Daily",
              "Weekly",
              "Quarterly or less"
            ],
            correct: 3,
            explanation: "Checking too often leads to anxiety and poor decisions. Long-term investors benefit from checking quarterly or less."
          }
        ]
      }
    ],
    finalQuiz: [
      {
        question: "What is the primary benefit of compound interest?",
        options: [
          "It provides guaranteed returns",
          "You earn interest on your interest, creating exponential growth",
          "It eliminates all investment risk",
          "It allows you to withdraw money anytime"
        ],
        correct: 1,
        explanation: "Compound interest means your earnings generate their own earnings over time."
      },
      {
        question: "Which investment typically offers the highest long-term returns but also the highest volatility?",
        options: [
          "Savings accounts",
          "Government bonds",
          "Stocks",
          "CDs (Certificates of Deposit)"
        ],
        correct: 2,
        explanation: "Stocks historically provide the best long-term returns but with more short-term volatility."
      },
      {
        question: "What is diversification?",
        options: [
          "Putting all your money in one high-performing stock",
          "Spreading investments across many different assets to reduce risk",
          "Only investing in bonds",
          "Timing the market perfectly"
        ],
        correct: 1,
        explanation: "Diversification means not putting all your eggs in one basket."
      },
      {
        question: "Using the Rule of 72, approximately how long does it take to double your money at 8% annual return?",
        options: [
          "5 years",
          "9 years",
          "12 years",
          "15 years"
        ],
        correct: 1,
        explanation: "72 ÷ 8 = 9 years to double your money."
      },
      {
        question: "What's the recommended order for investing priorities?",
        options: [
          "Individual stocks → 401(k) → Savings",
          "401(k) match → Emergency fund → Roth IRA → More 401(k)",
          "Crypto → Bonds → Stocks",
          "Savings only until you're 40"
        ],
        correct: 1,
        explanation: "Start with employer match (free money), then emergency fund, then tax-advantaged accounts."
      },
      {
        question: "What should you do when the market drops 20%?",
        options: [
          "Sell everything immediately",
          "Stop investing until it recovers",
          "Stay the course and continue your investment plan",
          "Move everything to cash"
        ],
        correct: 2,
        explanation: "Market drops are normal. Staying invested and continuing your plan typically leads to better outcomes."
      },
      {
        question: "What is inflation risk?",
        options: [
          "The risk that stocks will crash",
          "The risk that your returns won't keep up with rising prices",
          "The risk of losing your job",
          "The risk of paying too much in fees"
        ],
        correct: 1,
        explanation: "Inflation risk is the hidden danger of keeping too much in cash - your purchasing power erodes over time."
      },
      {
        question: "Why is starting to invest early so important?",
        options: [
          "You have more money when young",
          "Time allows compound interest to work, potentially doubling your returns",
          "Stocks are cheaper when you're young",
          "Banks give better rates to young people"
        ],
        correct: 1,
        explanation: "Time is your biggest advantage. Starting 10 years earlier can double your final wealth."
      }
    ]
  },
  "investor-insight": {
    id: "investor-insight",
    title: "Investor Insight",
    description: "Understand market psychology, indicators, and valuation.",
    level: "Intermediate",
    goal: "Develop the mindset to stay calm during market swings and avoid costly emotional decisions.",
    lessons: [
      {
        id: "what_moves_markets",
        title: "What Moves Markets",
        content: `
Markets don't move randomly. They respond to a mix of economic forces, news, and human behavior. Understanding these drivers helps you interpret market movements without overreacting.

---

## Economic Indicators

**GDP (Gross Domestic Product)**: Measures the total value of goods and services produced. Growing GDP usually means a healthy economy.

**Unemployment Rate**: High unemployment signals economic weakness. Low unemployment suggests strength but can lead to inflation.

**Inflation**: Rising prices erode purchasing power. Central banks raise interest rates to combat inflation, which affects stock and bond prices.

**Interest Rates**: When the Federal Reserve raises rates, borrowing becomes more expensive. This can slow economic growth and often causes stock prices to fall.

---

## Corporate Earnings

At the end of the day, stock prices reflect what companies earn. When companies report strong earnings, stock prices tend to rise. When earnings disappoint, prices fall.

**Earnings Season**: Four times a year, companies report quarterly results. These reports can cause significant price swings.

**Forward Guidance**: What companies say about the future often matters more than past results.

---

## News and Events

- **Geopolitical events**: Wars, elections, trade disputes
- **Industry news**: Regulatory changes, technological breakthroughs
- **Company-specific news**: Product launches, scandals, leadership changes

---

## Market Sentiment

Sometimes markets move based on mood rather than facts. Fear and greed drive short-term price swings that may not reflect underlying value.

**Key insight**: In the short term, markets are voting machines (popularity contests). In the long term, they're weighing machines (measuring actual value).
        `,
        quiz: [
          {
            question: "What typically happens to stock prices when the Federal Reserve raises interest rates?",
            options: [
              "They always go up",
              "They often decline as borrowing becomes more expensive",
              "Interest rates don't affect stocks",
              "Only bond prices are affected"
            ],
            correct: 1,
            explanation: "Higher interest rates increase borrowing costs for companies and make bonds more attractive relative to stocks."
          },
          {
            question: "What does 'forward guidance' refer to in earnings reports?",
            options: [
              "Past financial results",
              "What the company expects for future performance",
              "The stock's historical price",
              "Dividend payments"
            ],
            correct: 1,
            explanation: "Forward guidance is management's outlook for future quarters, which often moves stock prices more than past results."
          }
        ]
      },
      {
        id: "investor_psychology",
        title: "Investor Psychology",
        content: `
Behavioral finance research, including Nobel Prize-winning work by Daniel Kahneman and Richard Thaler, has shown that human brains are systematically wired to make poor investment decisions. Dalbar studies consistently find that the average stock fund investor earns 1 to 2 percentage points less per year than the fund itself, purely because of badly timed buying and selling driven by emotion. Understanding these biases is not optional; it is the single biggest edge a retail investor can develop.

---

## Fear and Greed: The Market's Two Engines

Markets cycle between fear and greed on every time scale, from intraday to multi-year.

**Greed (Euphoria Phase)**: Rising prices attract attention, which attracts more buyers, which drives prices higher. Media coverage turns positive. People who never invested start buying. Valuations stretch far beyond what fundamentals justify. This is how bubbles form: dot-com 1999, housing 2006, meme stocks 2021.

**Fear (Capitulation Phase)**: Falling prices trigger panic selling, which drives prices lower. Media coverage turns apocalyptic. Investors sell at the worst possible time, locking in losses. This is how bottoms form: March 2009, March 2020.

Warren Buffett's famous advice: "Be fearful when others are greedy, and greedy when others are fearful." This sounds simple but is psychologically almost impossible to execute without a system.

---

## The Core Cognitive Biases

### Loss Aversion
Kahneman and Tversky's Prospect Theory (1979) proved that losses feel approximately twice as painful as equivalent gains feel good. A $1,000 loss hurts more than a $1,000 gain pleases you. This causes two destructive behaviors:
- **Holding losers too long**: You refuse to sell a losing stock because selling makes the loss "real" (the disposition effect)
- **Selling winners too early**: You lock in gains quickly because you fear giving them back

The professional investor's mindset is the opposite: cut losses quickly and let winners run.

### Recency Bias
The brain gives disproportionate weight to recent events. After a year of gains, investors assume gains will continue and take on too much risk. After a crash, they assume losses will continue and flee to cash right when recovery begins. The S&P 500 has been positive in roughly 73% of calendar years since 1928, but it never feels that way during a drawdown.

### Herd Mentality (Social Proof)
Humans evolved in groups where following the crowd was a survival strategy. In markets, this instinct is destructive. By the time "everyone" is buying an asset, most of the upside is gone. By the time "everyone" is panicking, most of the downside has already occurred. The GameStop and AMC episodes of 2021 showed herd behavior amplified by social media at unprecedented speed.

### Confirmation Bias
Once you form an opinion about an investment, you unconsciously seek out information that supports it and dismiss evidence that contradicts it. If you believe Tesla is a great investment, you will find ten articles confirming your view and ignore five warning signs. This is why writing a pre-mortem (imagining your investment has already failed and listing why) is a powerful technique.

### Overconfidence Bias
Studies by Barber and Odean found that individual investors who traded the most earned the lowest returns. The average active trader underperformed a buy-and-hold index strategy by 6 to 7 percentage points annually. Overconfidence leads to excessive trading, concentrated bets, and ignoring diversification.

### Anchoring
You fixate on irrelevant reference points. If you bought a stock at $100 and it falls to $60, you anchor to $100 and wait to "get back to even" before selling, even if the fundamentals have deteriorated. The stock does not know or care what you paid for it.

### FOMO (Fear of Missing Out)
When you see others making money, especially on social media, you feel compelled to jump in. FOMO causes people to buy into already-overextended rallies. Bitcoin at $60,000 in 2021 attracted more retail buyers than Bitcoin at $4,000 in 2020, even though the risk-reward was vastly worse at the higher price.

### Mental Accounting
You treat money differently depending on where it came from. A tax refund or bonus feels like "free money," so you take more risk with it. But every dollar has the same value regardless of its source. Treating windfall money as play money leads to reckless speculation.

---

## The Behavior Gap: Real Numbers

The Dalbar Quantitative Analysis of Investor Behavior (QAIB) reports annually on this phenomenon:
- Over the 20 years ending 2023, the S&P 500 returned approximately 9.7% annually
- The average equity fund investor earned approximately 5.5% annually
- The 4.2% annual gap is almost entirely explained by behavioral mistakes: buying after rallies and selling after declines

On a $500/month contribution over 30 years, that gap represents over $400,000 in lost wealth. Behavioral mistakes are more expensive than fees, taxes, or bad stock picks combined.

---

## Systems That Defeat Your Biases

The key insight from behavioral finance is that you cannot simply decide to be rational. You need systems that remove emotion from the process.

### 1. Written Investment Policy Statement (IPS)
Before investing a dollar, write down: your goals, your target allocation, your rebalancing rules, and the conditions under which you will sell. When emotions surge, follow the document, not your gut.

### 2. Automate Everything
Set up automatic monthly contributions to your brokerage or retirement account. Dollar-cost averaging is not just a math strategy; it is a behavioral strategy. You never have to decide whether "now is a good time to invest."

### 3. The 72-Hour Rule
When you feel the urge to make an unplanned trade (buy or sell), wait 72 hours. If the urge is based on emotion, it will fade. If it is based on a genuine change in fundamentals, it will still be there in three days.

### 4. Portfolio Checkup Schedule
Check your portfolio quarterly at most. Checking daily or weekly increases anxiety and the likelihood of making emotional trades. Vanguard research shows that investors who check less frequently earn higher returns.

### 5. Precommitment Strategies
Tell a trusted person your investment plan. It is much harder to panic-sell when you have publicly committed to staying the course. Some investors even use account restrictions to make panic trading harder.

### 6. Reframe Crashes as Sales
When the market drops 20%, your automatic investments buy the same funds at 20% off. If your favorite store had a 20% off sale, you would buy more, not run away. Train your brain to view market dips the same way.

### 7. Study Market History
The S&P 500 has survived the Great Depression, World War II, the 1970s stagflation, the dot-com crash, the 2008 financial crisis, and COVID-19. Every time, it recovered and eventually reached new highs. Knowing this history makes it easier to stay invested during the next inevitable decline.
        `,
        quiz: [
          {
            question: "What does Warren Buffett mean by 'Be fearful when others are greedy'?",
            options: [
              "Always be afraid of the market",
              "When everyone is buying aggressively, be cautious as prices may be inflated",
              "Never invest when others are investing",
              "Greed is always bad"
            ],
            correct: 1,
            explanation: "When markets are euphoric, prices often become overvalued. Caution is warranted."
          },
          {
            question: "What is loss aversion?",
            options: [
              "Avoiding all investments",
              "The tendency for losses to feel roughly twice as painful as equivalent gains feel good",
              "Only investing in safe assets",
              "Selling at a loss"
            ],
            correct: 1,
            explanation: "Kahneman and Tversky's research showed we feel losses about twice as intensely as gains of the same size."
          },
          {
            question: "According to Dalbar studies, what is the approximate annual behavior gap for equity fund investors?",
            options: [
              "Less than 1%",
              "About 4% per year",
              "About 10% per year",
              "There is no gap"
            ],
            correct: 1,
            explanation: "The average equity investor earns roughly 4% less annually than the fund itself due to emotional buying and selling."
          },
          {
            question: "Why is the 72-hour rule effective?",
            options: [
              "It takes 72 hours for trades to settle",
              "Waiting 72 hours lets emotional impulses fade, preventing panic trades",
              "The SEC requires a 72-hour waiting period",
              "Stocks always recover within 72 hours"
            ],
            correct: 1,
            explanation: "Most emotional trading impulses fade within a few days. If the reason to trade is rational, it will still be valid after 72 hours."
          }
        ]
      },
      {
        id: "hype_vs_fundamentals",
        title: "Hype vs Fundamentals",
        content: `
One of the most important skills in investing is distinguishing between genuine value and hype. Many investors lose money chasing trends that have no substance.

---

## What Are Fundamentals?

Fundamentals are the actual financial health and performance of a company:

- **Revenue**: How much money the company brings in
- **Earnings**: How much profit it makes
- **Cash Flow**: Actual cash generated by operations
- **Debt**: How much the company owes
- **Assets**: What the company owns

These numbers tell you if a company is actually making money or just telling a good story.

---

## What Is Hype?

Hype is excitement based on stories, trends, or speculation rather than proven results:

- "This will be the next Amazon!"
- "Revolutionary technology will change everything!"
- "Everyone is buying it!"

Hype isn't always wrong—some hyped companies do become giants. But most don't.

---

## Red Flags

**No revenue or path to profitability**: The company has a cool idea but no business model.

**Valuation disconnected from reality**: A company worth billions but making no money.

**"This time is different"**: Every bubble uses this phrase.

**FOMO-driven buying**: You're buying because you're afraid of missing out, not because you've done research.

---

## How to Evaluate

1. **Look at the numbers**: Revenue growth, profit margins, cash flow
2. **Understand the business model**: How does the company actually make money?
3. **Compare to peers**: Is the valuation reasonable compared to similar companies?
4. **Ask: Would I buy this if no one else was talking about it?**

---

## The Dot-Com Lesson

In the late 1990s, companies with ".com" in their name skyrocketed regardless of whether they made money. Most went to zero. The few that survived (Amazon, eBay) had real businesses underneath the hype.
        `,
        quiz: [
          {
            question: "What's a key difference between fundamentals and hype?",
            options: [
              "There is no difference",
              "Fundamentals are based on actual financial performance; hype is based on stories and speculation",
              "Hype is always more accurate",
              "Fundamentals only matter for bonds"
            ],
            correct: 1,
            explanation: "Fundamentals reflect real business performance, while hype is often driven by excitement and speculation."
          },
          {
            question: "What's a red flag when evaluating a hyped investment?",
            options: [
              "Strong revenue growth",
              "Valuation disconnected from actual earnings or revenue",
              "Positive cash flow",
              "Low debt levels"
            ],
            correct: 1,
            explanation: "When a company's valuation doesn't match its financial reality, that's a warning sign."
          }
        ]
      },
      {
        id: "types_of_investing",
        title: "Types of Investing",
        content: `
There's no single "right" way to invest. Different approaches suit different goals, time horizons, and personalities.

---

## Passive Investing

**What it is**: Buy and hold a diversified portfolio, usually through index funds. Don't try to beat the market—just match it.

**Pros**:
- Low fees
- Less time required
- Historically outperforms most active strategies

**Best for**: Most people, especially beginners

---

## Active Investing

**What it is**: Try to beat the market by picking individual stocks or timing when to buy and sell.

**Pros**:
- Potential for higher returns
- More engaging for those who enjoy research

**Cons**:
- Higher fees
- Most active managers underperform indexes
- Requires significant time and skill

---

## Value Investing

**What it is**: Buy stocks that appear undervalued based on fundamentals. Look for companies trading below their intrinsic worth.

**Famous practitioners**: Warren Buffett, Benjamin Graham

**Key metrics**: P/E ratio, P/B ratio, dividend yield

---

## Growth Investing

**What it is**: Buy companies expected to grow faster than average, even if they're expensive now.

**Focus**: Revenue growth, market opportunity, innovation

**Risk**: High valuations can lead to big losses if growth disappoints

---

## Income Investing

**What it is**: Focus on investments that generate regular income through dividends or interest.

**Typical investments**: Dividend stocks, bonds, REITs

**Best for**: Retirees or those seeking steady cash flow

---

## Which Is Right for You?

Most beginners should start with passive investing through index funds. As you learn more, you might incorporate other strategies. Many successful investors use a combination.
        `,
        quiz: [
          {
            question: "What is passive investing?",
            options: [
              "Actively trading stocks daily",
              "Buying and holding diversified index funds to match market returns",
              "Only investing in bonds",
              "Trying to beat the market through stock picking"
            ],
            correct: 1,
            explanation: "Passive investing means matching the market through index funds rather than trying to beat it."
          },
          {
            question: "Who is value investing associated with?",
            options: [
              "Day traders",
              "Warren Buffett and Benjamin Graham",
              "Only hedge funds",
              "Cryptocurrency investors"
            ],
            correct: 1,
            explanation: "Value investing was pioneered by Benjamin Graham and made famous by Warren Buffett."
          }
        ]
      },
      {
        id: "risk_portfolio_thinking",
        title: "Risk and Portfolio Thinking",
        content: `
Understanding risk isn't just about avoiding losses—it's about building a portfolio that matches your goals and lets you sleep at night.

---

## Types of Risk

**Market Risk**: The entire market declines (like 2008 or 2020). Even good companies fall.

**Company Risk**: A specific company fails or underperforms. This is why you diversify.

**Inflation Risk**: Your returns don't keep up with rising prices.

**Interest Rate Risk**: Rising rates hurt bond prices and can affect stocks.

**Concentration Risk**: Too much money in one stock, sector, or asset class.

---

## Diversification

Don't put all your eggs in one basket. Spread investments across:

- **Asset classes**: Stocks, bonds, real estate
- **Sectors**: Technology, healthcare, finance, etc.
- **Geographies**: US, international, emerging markets
- **Company sizes**: Large-cap, mid-cap, small-cap

---

## Asset Allocation

Your mix of stocks, bonds, and other assets is the most important investment decision. It determines:

- How much your portfolio might grow
- How much it might drop in a bad year
- How volatile the ride will be

**Common allocations**:
- Aggressive (80% stocks, 20% bonds): For young investors with decades ahead
- Moderate (60% stocks, 40% bonds): Balanced approach
- Conservative (40% stocks, 60% bonds): For those near retirement

---

## Rebalancing

Over time, your allocation drifts as different assets perform differently. Rebalancing means periodically adjusting back to your target mix.

**Example**: If stocks surge and your 60/40 portfolio becomes 70/30, you'd sell some stocks and buy bonds to get back to 60/40.
        `,
        interactiveElements: ['RiskReturnChart', 'DiversificationDemo'],
        quiz: [
          {
            question: "What is the main purpose of diversification?",
            options: [
              "To guarantee profits",
              "To reduce the impact of any single investment failing",
              "To maximize returns",
              "To avoid all risk"
            ],
            correct: 1,
            explanation: "Diversification spreads risk so that one bad investment doesn't devastate your portfolio."
          },
          {
            question: "What is rebalancing?",
            options: [
              "Selling all your investments",
              "Adjusting your portfolio back to your target allocation",
              "Only buying more stocks",
              "Checking your balance"
            ],
            correct: 1,
            explanation: "Rebalancing means periodically adjusting your holdings to maintain your desired asset mix."
          }
        ]
      },
      {
        id: "reading_market_signals",
        title: "Reading Market Signals",
        content: `
Markets constantly send signals about direction, risk, and investor behavior. Learning to read these patterns helps you respond strategically instead of emotionally.

---

## Trends

A trend describes the general direction of market movement over time.

**Uptrend**: Prices make higher highs and higher lows. Buyers are in control.

**Downtrend**: Prices make lower highs and lower lows. Sellers are in control.

**Sideways**: Prices move within a range. Neither buyers nor sellers dominate.

---

## Volatility

Volatility measures how much prices fluctuate.

**Low volatility**: Calm markets, small price changes

**High volatility**: Uncertainty, large rapid price swings

Volatility isn't necessarily bad—it means movement and opportunity. But it also means risk.

---

## Volume

Volume shows how many shares are being traded.

**High volume**: Strong conviction behind price moves

**Low volume**: Less conviction, moves may not be sustainable

Volume confirms trends. A price rise on high volume is more meaningful than one on low volume.

---

## Support and Resistance

**Support**: A price level where buying pressure tends to emerge, stopping declines.

**Resistance**: A price level where selling pressure tends to emerge, stopping advances.

These levels represent psychological barriers where many investors make decisions.

---

## Key Insight

You don't need to predict every market move. Understanding these signals helps you:
- Avoid panic selling during normal corrections
- Recognize when trends might be changing
- Make more informed decisions about when to buy or sell
        `,
        quiz: [
          {
            question: "What does an uptrend typically show?",
            options: [
              "Lower highs and lower lows",
              "Higher highs and higher lows",
              "No clear pattern",
              "Only volume matters"
            ],
            correct: 1,
            explanation: "An uptrend is defined by a series of higher highs and higher lows, showing buyers are in control."
          },
          {
            question: "What does high volume during a price move indicate?",
            options: [
              "The move is likely weak",
              "Strong conviction behind the move",
              "Volume doesn't matter",
              "The market is closed"
            ],
            correct: 1,
            explanation: "High volume suggests many investors agree with the direction, making the move more significant."
          }
        ]
      }
    ],
    finalQuiz: [
      {
        question: "What is loss aversion?",
        options: [
          "Avoiding all risky investments",
          "The tendency for losses to feel worse than equivalent gains feel good",
          "Selling investments at a loss",
          "Being afraid of the stock market"
        ],
        correct: 1,
        explanation: "Loss aversion is a cognitive bias where we feel losses more intensely than gains of the same size."
      },
      {
        question: "What is recency bias in investing?",
        options: [
          "Only investing in recent IPOs",
          "Assuming recent trends will continue indefinitely",
          "Preferring recently founded companies",
          "Checking your portfolio recently"
        ],
        correct: 1,
        explanation: "Recency bias leads us to overweight recent events when making predictions about the future."
      },
      {
        question: "What typically happens when the Federal Reserve raises interest rates?",
        options: [
          "Stock prices always go up",
          "Borrowing becomes more expensive, often causing stock prices to decline",
          "Nothing changes",
          "Only bonds are affected"
        ],
        correct: 1,
        explanation: "Higher interest rates increase costs for companies and make bonds more attractive relative to stocks."
      },
      {
        question: "What is the main advantage of passive investing?",
        options: [
          "It guarantees beating the market",
          "Low fees and historically outperforms most active strategies",
          "It requires constant monitoring",
          "It only works in bull markets"
        ],
        correct: 1,
        explanation: "Passive investing through index funds has low fees and historically beats most active managers."
      },
      {
        question: "What does support level mean in technical analysis?",
        options: [
          "A price where selling pressure emerges",
          "A price level where buying pressure tends to stop declines",
          "The highest price ever reached",
          "The company's customer support"
        ],
        correct: 1,
        explanation: "Support is a price level where buying interest tends to emerge, preventing further declines."
      }
    ]
  },
  "applied-investing": {
    id: "applied-investing",
    title: "Applied Investing",
    description: "Put knowledge into practice with portfolios, taxes, and strategies.",
    level: "Advanced",
    goal: "Build a complete, diversified portfolio strategy you can execute this week.",
    lessons: [
      {
        id: "costs_fees_taxes",
        title: "Costs, Fees, and Tax Planning",
        content: `
Every dollar lost to fees or avoidable taxes is a dollar that can never compound for you. Tax planning is not about cheating the system; it is about using the structures Congress created to encourage saving and investing. This lesson covers everything from fund costs to a complete tax strategy.

---

## Expense Ratios: The Silent Wealth Killer

Expense ratios are annual fees charged by funds, expressed as a percentage of assets under management. They are deducted automatically, so you never write a check, but they erode returns every single year.

| Fund Type | Typical Expense Ratio | Cost on $100K/year |
|-----------|----------------------|-------------------|
| Vanguard Total Stock (VTI) | 0.03% | $30 |
| Average active large-cap fund | 0.70% | $700 |
| Hedge fund (2/20 structure) | ~2.00% + 20% of gains | $2,000+ |

Over 30 years at 7% average returns, a 1% fee difference costs roughly 25% of your ending wealth. On a $500/month contribution, that is over $150,000 lost to fees alone. Always check the expense ratio before buying any fund.

---

## Capital Gains Tax: Short-Term vs. Long-Term

When you sell an investment for more than you paid, the profit is a capital gain. The IRS taxes these gains differently depending on how long you held the asset.

**Short-term capital gains** (held less than one year): Taxed at your ordinary income rate, which can be as high as 37% federally.

**Long-term capital gains** (held one year or longer): Taxed at preferential rates.

| Taxable Income (Single Filer 2024) | Long-Term Rate |
|------------------------------------|---------------|
| Up to $47,025 | 0% |
| $47,026 to $518,900 | 15% |
| Over $518,900 | 20% |

**Key takeaway**: Simply holding an investment for 366 days instead of 364 days can cut your tax rate roughly in half. Long-term thinking is rewarded by the tax code.

---

## Dividend Taxation

Not all dividends are taxed the same way.

**Qualified dividends** (most US stock dividends) are taxed at the favorable long-term capital gains rates: 0%, 15%, or 20%.

**Ordinary (non-qualified) dividends** are taxed as regular income. Bond interest, REIT distributions, and certain foreign dividends fall into this category.

If you hold dividend-paying stocks in a taxable account, pay attention to whether the dividends are qualified. Holding the stock for at least 61 days around the ex-dividend date is required for qualification.

---

## Tax-Advantaged Accounts: Your Most Powerful Tools

Congress created several account types specifically designed to encourage retirement saving and investing. Understanding each one is critical to an efficient tax plan.

### Traditional 401(k) and Traditional IRA
- Contributions reduce your taxable income today (tax deduction)
- Money grows tax-deferred (no taxes on dividends or gains while inside)
- Withdrawals in retirement are taxed as ordinary income
- Best when you expect to be in a lower tax bracket in retirement than you are now

### Roth 401(k) and Roth IRA
- Contributions are made with after-tax dollars (no deduction today)
- Money grows completely tax-free
- Qualified withdrawals in retirement are tax-free (zero tax on decades of growth)
- Best when you expect your tax bracket to stay the same or increase
- Roth IRA contributions (not earnings) can be withdrawn anytime without penalty

### HSA (Health Savings Account)
- Triple tax advantage: deductible contributions, tax-free growth, tax-free withdrawals for medical expenses
- After age 65, non-medical withdrawals are taxed as income (like a Traditional IRA), but medical withdrawals remain tax-free
- Strategy: pay medical expenses out-of-pocket now, invest the HSA, and reimburse yourself years later for decades of tax-free growth

### 529 Plan (Education Savings)
- State tax deduction in many states
- Tax-free growth and withdrawals for qualified education expenses
- Can be used for K-12 tuition (up to $10,000/year) and college costs
- Unused funds can be rolled into a Roth IRA for the beneficiary (new rule, lifetime limit of $35,000)

---

## Asset Location: Where You Hold Matters

Asset location is the strategy of placing investments in the right account type to minimize taxes. This is different from asset allocation (what you own).

**In tax-advantaged accounts (401k, IRA):** Place tax-inefficient investments
- Bonds (interest taxed as ordinary income)
- REITs (dividends taxed as ordinary income)
- Actively managed funds (frequent trading generates short-term gains)
- High-dividend stocks

**In taxable brokerage accounts:** Place tax-efficient investments
- US total market index funds (low turnover, mostly qualified dividends)
- International stock funds (you get a Foreign Tax Credit)
- Municipal bonds (interest is federally tax-free, and state-tax-free if issued in your state)
- ETFs over mutual funds (ETFs are structurally more tax-efficient due to in-kind creation/redemption)

Proper asset location can add 0.50% to 0.75% to your after-tax annual return without taking any additional risk.

---

## Tax-Loss Harvesting

Tax-loss harvesting is selling investments at a loss to offset capital gains or reduce taxable income.

**How it works:**
1. Sell an investment that has declined in value
2. Use the realized loss to offset capital gains from other sales
3. If losses exceed gains, deduct up to $3,000 against ordinary income per year
4. Carry forward any remaining losses indefinitely to future years
5. Immediately buy a similar (but not "substantially identical") investment to maintain market exposure

**Example:** You sell VTI at a $5,000 loss and buy VOO immediately. You maintain essentially the same market exposure but harvest a $5,000 tax loss. At a 22% tax bracket, that saves $1,100 in taxes.

**The Wash Sale Rule:** You cannot buy a "substantially identical" security within 30 days before or after selling at a loss. VTI and VOO are considered different enough. VTI and VTSAX (Vanguard Total Stock Market Admiral shares) are substantially identical.

---

## Tax Planning by Life Stage

**In your 20s and 30s:** Prioritize Roth contributions (you are likely in a lower bracket now). Max out employer 401(k) match. Start an HSA if eligible. Your long time horizon maximizes the value of tax-free compounding.

**In your 40s and 50s:** Evaluate whether Traditional or Roth is better as your income peaks. Consider backdoor Roth IRA conversions if over the income limit. Begin tax-loss harvesting intentionally in taxable accounts.

**Approaching retirement:** Plan Roth conversion ladders to fill up lower tax brackets. Understand Required Minimum Distributions (RMDs) from Traditional accounts starting at age 73. Consider charitable giving strategies (Qualified Charitable Distributions from IRAs).

---

## The Order of Operations for Tax-Efficient Investing

1. Contribute enough to your 401(k) to get the full employer match (free money)
2. Max out your HSA if you have a high-deductible health plan
3. Max out your Roth IRA ($7,000 in 2024, $8,000 if age 50+)
4. Go back and max out your 401(k) ($23,000 in 2024, $30,500 if age 50+)
5. Invest in a taxable brokerage account with tax-efficient index funds
6. Consider a 529 plan if you have children or education goals

This sequence prioritizes accounts with the highest tax benefits and flexibility first.

---

## Common Tax Mistakes to Avoid

- **Not contributing enough to get the full employer match** (leaving free money on the table)
- **Holding bonds in taxable accounts** (bond interest is taxed at your highest rate)
- **Selling winners too early** (converting long-term gains into short-term gains)
- **Ignoring the 0% long-term capital gains bracket** (if your income is low enough, you pay zero tax on gains)
- **Forgetting state taxes** (some states have no income tax; municipal bonds from your state are often double tax-free)
- **Cashing out a 401(k) when changing jobs** (triggers income tax plus a 10% penalty if under 59.5)
        `,
        quiz: [
          {
            question: "Why does a 1% expense ratio matter over 30 years?",
            options: [
              "It doesn't matter much",
              "It compounds and can cost roughly 25% of your potential wealth",
              "Expense ratios are tax-deductible",
              "Only bonds have expense ratios"
            ],
            correct: 1,
            explanation: "Fees compound against you every year, potentially costing 25% or more of your ending wealth over decades."
          },
          {
            question: "What's the advantage of long-term capital gains over short-term?",
            options: [
              "There is no difference",
              "Long-term gains are typically taxed at lower rates (0%, 15%, or 20%)",
              "Short-term gains are always better",
              "Only dividends are taxed"
            ],
            correct: 1,
            explanation: "Holding investments for more than one year qualifies for preferential long-term capital gains rates."
          },
          {
            question: "What is asset location?",
            options: [
              "Choosing which country to invest in",
              "Placing tax-inefficient investments in tax-advantaged accounts and vice versa",
              "Storing physical gold in a safe",
              "Picking the cheapest brokerage"
            ],
            correct: 1,
            explanation: "Asset location means putting bonds and REITs in 401k/IRA (tax-sheltered) and index funds in taxable accounts."
          },
          {
            question: "What is the Wash Sale Rule?",
            options: [
              "You must wash your hands before trading",
              "You cannot buy a substantially identical security within 30 days of selling it at a loss",
              "You must sell a stock within 30 days of buying it",
              "It only applies to bonds"
            ],
            correct: 1,
            explanation: "The IRS disallows a tax loss if you repurchase a substantially identical investment within 30 days before or after the sale."
          },
          {
            question: "Which account has a triple tax advantage?",
            options: [
              "Roth IRA",
              "Traditional 401(k)",
              "HSA (Health Savings Account)",
              "Taxable brokerage"
            ],
            correct: 2,
            explanation: "HSAs offer tax-deductible contributions, tax-free growth, and tax-free withdrawals for medical expenses."
          }
        ]
      },
      {
        id: "what_to_do_in_crash",
        title: "What to Do in a Market Crash",
        content: `
Market crashes are scary. Your portfolio drops 20%, 30%, maybe more. Headlines scream disaster. Your instincts tell you to sell everything.

Here's the thing: what you do during a crash often determines your long-term investing success.

---

## First: Don't Panic Sell

This is the most important rule. Selling during a crash locks in your losses and means you miss the recovery.

**Historical fact**: Every major crash in history has eventually recovered. The investors who stayed invested came out ahead.

- 1987 crash: Recovered in 2 years
- 2008 financial crisis: Recovered in 4 years
- 2020 COVID crash: Recovered in 5 months

---

## Second: Remember Your Timeline

If you're investing for retirement 20+ years away, a crash today is just noise. You have time to recover.

Ask yourself: "Am I going to need this money in the next 5 years?" If no, stay the course.

---

## Third: Consider Buying More

Crashes mean stocks are "on sale." If you have cash available and a long time horizon, buying during crashes can significantly boost your long-term returns.

**Dollar-cost averaging**: Continue your regular investments through the crash. You'll buy more shares at lower prices.

---

## Fourth: Review Your Allocation

A crash is a good time to check if your portfolio matches your risk tolerance. If you can't sleep at night, you might be too aggressive.

But don't make changes during the panic. Wait until markets stabilize, then reassess calmly.

---

## What NOT to Do

- Don't check your portfolio daily
- Don't watch financial news constantly
- Don't try to time the bottom
- Don't make permanent decisions based on temporary emotions
        `,
        quiz: [
          {
            question: "What's the most important rule during a market crash?",
            options: [
              "Sell everything immediately",
              "Don't panic sell—stay invested",
              "Check your portfolio hourly",
              "Move everything to cash"
            ],
            correct: 1,
            explanation: "Panic selling locks in losses and means you miss the recovery. Stay the course."
          },
          {
            question: "What does history show about major market crashes?",
            options: [
              "Markets never recover",
              "Every major crash has eventually recovered",
              "Only some crashes recover",
              "Recovery takes 50+ years"
            ],
            correct: 1,
            explanation: "Every major crash in history has recovered, though recovery times vary."
          }
        ]
      },
      {
        id: "setting_long_term_structure",
        title: "Setting a Long-Term Structure",
        content: `
Successful investing isn't about making perfect decisions. It's about setting up a system that works over decades.

---

## The Three-Fund Portfolio

A simple, effective structure used by millions:

1. **US Total Stock Market Index Fund**: Captures the entire US market
2. **International Stock Index Fund**: Diversifies globally
3. **Total Bond Market Index Fund**: Provides stability

That's it. Three funds can give you a complete, diversified portfolio.

---

## Automation Is Your Friend

Set up automatic investments so you don't have to think about it:

- Automatic 401(k) contributions from your paycheck
- Automatic transfers to your IRA each month
- Automatic reinvestment of dividends

When investing is automatic, you remove emotion and ensure consistency.

---

## Rebalancing Schedule

Pick a schedule and stick to it:

- **Annual rebalancing**: Check once a year, adjust if needed
- **Threshold rebalancing**: Rebalance when allocation drifts more than 5-10%

Don't rebalance too often—it can trigger taxes and fees.

---

## Emergency Fund First

Before investing aggressively, ensure you have 3-6 months of expenses in cash. This prevents you from having to sell investments during emergencies.

---

## The Investment Policy Statement

Write down your plan:
- Your goals and timeline
- Your target allocation
- When you'll rebalance
- What you'll do during crashes

Having a written plan helps you stay disciplined when emotions run high.
        `,
        quiz: [
          {
            question: "What is the three-fund portfolio?",
            options: [
              "Three individual stocks",
              "US stocks, international stocks, and bonds—a simple diversified approach",
              "Three different brokerages",
              "Only for professional investors"
            ],
            correct: 1,
            explanation: "The three-fund portfolio provides complete diversification with just US stocks, international stocks, and bonds."
          },
          {
            question: "Why is automation important in investing?",
            options: [
              "It guarantees returns",
              "It removes emotion and ensures consistent investing",
              "It's required by law",
              "It only works for large amounts"
            ],
            correct: 1,
            explanation: "Automatic investing removes the temptation to time the market and ensures you invest consistently."
          }
        ]
      },
      {
        id: "realistic_expectations",
        title: "Realistic Expectations About Returns",
        content: `
One of the biggest mistakes investors make is having unrealistic expectations. Let's set some grounded expectations based on history.

---

## Historical Stock Returns

The S&P 500 has returned about **10% annually** on average over the long term (before inflation).

After inflation, that's about **7% real returns**.

**Important**: This is an average. Individual years vary wildly:
- Some years: +30%
- Some years: -30%
- Most years: Somewhere in between

---

## What 7% Real Returns Means

Using the Rule of 72: Your money doubles roughly every 10 years.

- $10,000 at age 25 → ~$80,000 at age 55
- $500/month for 30 years → ~$500,000

This is life-changing wealth, but it takes time.

---

## What's NOT Realistic

- Doubling your money in a year (without extreme risk)
- Consistent 20%+ annual returns
- Never having a down year
- Timing the market perfectly

Anyone promising these is either lying or taking enormous risks.

---

## Sequence of Returns Risk

The order of returns matters, especially near retirement. A crash right before you retire hurts more than a crash early in your career.

This is why you gradually shift to more conservative allocations as you approach your goal.

---

## The Power of Consistency

Slow and steady wins the race. A boring portfolio of index funds, held for decades, beats most "exciting" strategies.

**The real secret**: Start early, invest consistently, keep costs low, stay the course.
        `,
        interactiveElements: ['CompoundCalculator'],
        quiz: [
          {
            question: "What is the historical average annual return of the S&P 500?",
            options: [
              "About 3%",
              "About 10% (7% after inflation)",
              "About 20%",
              "It varies too much to say"
            ],
            correct: 1,
            explanation: "Historically, the S&P 500 has returned about 10% annually, or 7% after adjusting for inflation."
          },
          {
            question: "What's the 'secret' to successful long-term investing?",
            options: [
              "Finding the next hot stock",
              "Timing the market perfectly",
              "Start early, invest consistently, keep costs low, stay the course",
              "Only investing during bull markets"
            ],
            correct: 2,
            explanation: "Consistency and patience beat trying to outsmart the market."
          }
        ]
      },
      {
        id: "asset_allocation",
        title: "Asset Allocation",
        content: `
Asset allocation—how you divide your money between stocks, bonds, and other assets—is the most important investment decision you'll make.

---

## Why It Matters

Studies show that asset allocation explains about **90% of portfolio returns** over time. Stock picking and market timing? Much less important.

Your allocation determines:
- How much your portfolio might grow
- How much it might drop in a bad year
- How bumpy the ride will be

---

## The Basic Framework

**Stocks**: Higher growth, more volatility. Good for long time horizons.

**Bonds**: Lower growth, more stability. Good for shorter horizons or reducing risk.

**Cash**: Safest, but loses to inflation. Keep enough for emergencies.

---

## Common Allocations

**Aggressive (80/20 stocks/bonds)**: For young investors with 20+ years.

**Moderate (60/40)**: Classic balanced portfolio. Less volatility.

**Conservative (40/60)**: For those near retirement or risk-averse.

---

## Target-Date Funds

If this feels overwhelming, consider target-date funds. Pick the fund matching your retirement year, and it automatically adjusts allocation as you age.

Example: "Target 2055 Fund" starts aggressive and gradually becomes conservative.

---

## The Simple Approach

A common rule of thumb: Your age in bonds, the rest in stocks.
- Age 30: 30% bonds, 70% stocks
- Age 50: 50% bonds, 50% stocks

It's not perfect, but it's a reasonable starting point.
        `,
        quiz: [
          {
            question: "What percentage of portfolio returns does asset allocation explain?",
            options: [
              "About 10%",
              "About 50%",
              "About 90%",
              "100%"
            ],
            correct: 2,
            explanation: "Research shows asset allocation is the primary driver of long-term returns."
          },
          {
            question: "What is a target-date fund?",
            options: [
              "A fund that only invests on certain dates",
              "A fund that automatically adjusts allocation as you approach retirement",
              "A fund for day traders",
              "A fund that guarantees returns by a target date"
            ],
            correct: 1,
            explanation: "Target-date funds automatically shift from aggressive to conservative as you near your target retirement year."
          }
        ]
      },
      {
        id: "lending_home_ownership",
        title: "Lending, Mortgages, and Home Ownership",
        content: `
For most people, buying a home is the single largest financial transaction of their lives. It is simultaneously a place to live and, potentially, an investment. Understanding how lending works, what a mortgage really costs, and how home ownership fits into your broader financial picture is essential knowledge.

---

## How Lending Works: The Basics

When a bank lends you money, they are taking a risk that you might not pay them back. The interest rate they charge compensates them for that risk, their cost of capital, and their profit margin.

**Key terms every borrower must know:**
- **Principal**: The amount you borrow
- **Interest Rate**: The annual cost of borrowing, expressed as a percentage
- **APR (Annual Percentage Rate)**: The true cost of the loan including fees, points, and other charges. Always compare APR, not just the interest rate
- **Amortization**: The schedule by which your monthly payments gradually shift from mostly interest to mostly principal
- **Term**: The length of the loan (15 years, 30 years, etc.)
- **Collateral**: The asset the lender can seize if you default (for a mortgage, this is your home)

---

## Your Credit Score: The Price Tag on Your Borrowing

Your credit score (FICO score, ranging 300 to 850) is the single most important number in determining what interest rate you receive. A higher score means a lower rate, which means less money paid over the life of the loan.

| FICO Score Range | Rating | Approximate 30-Year Mortgage Rate (2024) |
|-----------------|--------|----------------------------------------|
| 760 and above | Excellent | 6.5% |
| 700 to 759 | Good | 6.8% |
| 660 to 699 | Fair | 7.2% |
| 620 to 659 | Below Average | 7.8% |
| Below 620 | Poor | May not qualify for conventional |

On a $400,000 mortgage, the difference between a 6.5% rate and a 7.8% rate is approximately $130,000 in additional interest over 30 years. Improving your credit score before applying for a mortgage can save you more than almost any other single financial action.

**How to build and maintain good credit:**
- Pay every bill on time (payment history is 35% of your FICO score)
- Keep credit card utilization below 30% of your limit (ideally below 10%)
- Keep old credit accounts open (length of credit history matters)
- Avoid opening many new accounts at once (hard inquiries)
- Check your credit report annually for errors at AnnualCreditReport.com

---

## Types of Mortgages

### Fixed-Rate Mortgage (15-Year or 30-Year)
The interest rate and monthly payment never change for the life of the loan. This is the most common and most predictable option.

**30-year fixed**: Lower monthly payments, more total interest paid. Good for cash flow flexibility.

**15-year fixed**: Higher monthly payments (roughly 30 to 40 percent more), but significantly less total interest. You build equity faster and own your home in half the time.

| | 30-Year at 6.5% | 15-Year at 6.0% |
|---|---|---|
| Loan Amount | $400,000 | $400,000 |
| Monthly Payment | $2,528 | $3,375 |
| Total Interest Paid | $510,177 | $207,487 |
| Total Cost | $910,177 | $607,487 |

The 15-year mortgage costs $302,690 less in total, but requires $847 more per month.

### Adjustable-Rate Mortgage (ARM)
The rate is fixed for an initial period (typically 5 or 7 years), then adjusts periodically based on a market index. ARMs usually start with a lower rate than fixed mortgages.

**5/1 ARM**: Fixed for 5 years, then adjusts annually. Risky if you plan to stay long-term. Can make sense if you are confident you will move or refinance within the fixed period.

**Important protections**: Most ARMs have rate caps (e.g., cannot increase more than 2% per adjustment, or 5% over the life of the loan). Always understand the caps before signing.

### FHA Loans
Government-insured loans with lower down payment requirements (as low as 3.5%) and more flexible credit standards. Requires mortgage insurance (MIP) for the life of the loan unless you refinance. Good for first-time buyers who cannot save a 20% down payment.

### VA Loans
Available to veterans and active-duty military. Often require zero down payment and no private mortgage insurance. Typically offer competitive interest rates. One of the best loan products available, if you qualify.

---

## The True Cost of Home Ownership

The purchase price is just the beginning. Homeowners must budget for ongoing costs that renters do not face.

**Monthly costs beyond the mortgage payment:**
- Property taxes (typically 1% to 2% of home value per year, varies by location)
- Homeowner's insurance (typically $1,000 to $3,000 per year)
- Private Mortgage Insurance (PMI) if down payment is less than 20% (typically 0.5% to 1% of loan value per year; drops off once you reach 20% equity)
- HOA fees if applicable ($200 to $500+ per month in some areas)
- Maintenance and repairs (budget 1% to 2% of home value per year)
- Utilities (often higher than renting due to larger space)

**The 28/36 Rule**: Lenders generally prefer that your housing costs (principal, interest, taxes, insurance) do not exceed 28% of your gross monthly income, and your total debt payments do not exceed 36%.

---

## Rent vs. Buy: The Real Math

The decision to rent or buy is not as simple as "building equity vs. throwing money away." Both have real costs.

**Arguments for buying:**
- Build equity over time (forced savings)
- Fixed housing costs with a fixed-rate mortgage (rent increases annually)
- Tax deduction for mortgage interest (only if you itemize)
- Potential price appreciation
- Stability and control over your living space

**Arguments for renting:**
- No maintenance or repair costs
- Greater flexibility to relocate
- Lower upfront costs (no down payment, closing costs, etc.)
- Can invest the difference between renting and buying in the stock market
- No risk of home price decline

**The Break-Even Horizon**: It typically takes 5 to 7 years for buying to become cheaper than renting the same property, accounting for closing costs (2% to 5% of purchase price), transaction costs when selling (5% to 6% in agent commissions), and the opportunity cost of the down payment. If you plan to move within 5 years, renting is almost always cheaper.

---

## The Down Payment Decision

**20% down**: Avoids PMI, gives you lower monthly payments, and better loan terms. On a $400,000 home, that is $80,000.

**Less than 20%**: Allows you to buy sooner, but you pay PMI (typically $100 to $300 per month on a $400,000 loan) until you reach 20% equity. FHA loans allow as low as 3.5% down.

**Should you drain your investments for a bigger down payment?** Generally no. If your investments earn 8% to 10% over time and your mortgage rate is 6.5%, the math favors keeping investments and paying PMI temporarily. However, this depends on your risk tolerance and the size of the PMI payment. Never deplete your emergency fund for a down payment.

---

## Refinancing: When It Makes Sense

Refinancing replaces your current mortgage with a new one at different terms. It makes sense when:
- Interest rates have dropped at least 0.75% to 1% below your current rate
- You can recoup closing costs within 2 to 3 years (divide closing costs by monthly savings)
- You want to switch from an ARM to a fixed rate before the adjustment period
- You want to remove PMI by refinancing into a conventional loan with 20%+ equity
- You want to shorten your term (e.g., 30-year to 15-year) while rates are low

Refinancing is not free. Closing costs typically run 2% to 3% of the loan amount. Always calculate the break-even point.

---

## Home Ownership as an Investment

Historically, US home prices have appreciated at roughly 3% to 4% per year on average (per the Case-Shiller Index), which barely beats inflation. The S&P 500 has returned roughly 10% per year over the same period.

**A home is a lifestyle asset first and an investment second.** Buy a home because you want to live in it for the long term, not primarily as an investment. The real financial benefit of home ownership comes from forced savings (building equity through mortgage payments) and the ability to lock in your housing costs with a fixed-rate mortgage.

**Do not**: Buy more house than you can afford hoping prices will go up. The 2008 housing crisis was caused by exactly this thinking.

**Do**: Buy a home you can comfortably afford, maintain it well, and let any appreciation be a bonus rather than the plan.
        `,
        quiz: [
          {
            question: "Why should you compare APR rather than just the interest rate when shopping for a mortgage?",
            options: [
              "APR is always lower than the interest rate",
              "APR includes fees and other costs, giving you the true cost of borrowing",
              "APR only applies to adjustable-rate mortgages",
              "There is no difference between APR and interest rate"
            ],
            correct: 1,
            explanation: "APR captures the total cost of the loan including origination fees, points, and other charges, making it a better comparison tool."
          },
          {
            question: "What is the typical break-even horizon for buying vs. renting?",
            options: [
              "1 year",
              "5 to 7 years",
              "15 to 20 years",
              "It is always cheaper to buy"
            ],
            correct: 1,
            explanation: "After accounting for closing costs, transaction costs, and opportunity costs, buying typically breaks even with renting after 5 to 7 years."
          },
          {
            question: "What happens when you put less than 20% down on a conventional mortgage?",
            options: [
              "Nothing, there is no penalty",
              "You must pay Private Mortgage Insurance (PMI) until you reach 20% equity",
              "Your interest rate is automatically doubled",
              "You cannot get a fixed-rate mortgage"
            ],
            correct: 1,
            explanation: "PMI protects the lender against default and is required until you build 20% equity. It typically adds $100 to $300 per month."
          },
          {
            question: "Historically, how do average home price returns compare to stock market returns?",
            options: [
              "Homes appreciate much faster than stocks",
              "Homes appreciate at roughly 3-4% per year, while stocks average roughly 10%",
              "Homes and stocks return the same amount",
              "Homes never appreciate in value"
            ],
            correct: 1,
            explanation: "Home prices historically barely beat inflation (3-4%), while the S&P 500 has averaged roughly 10%. A home is a lifestyle asset, not primarily an investment."
          },
          {
            question: "What is the 28/36 rule?",
            options: [
              "You should save 28% and invest 36% of income",
              "Housing costs should not exceed 28% of gross income, total debt should not exceed 36%",
              "You need a credit score of at least 728 to buy a home",
              "You should refinance every 28 to 36 months"
            ],
            correct: 1,
            explanation: "The 28/36 rule is a lender guideline that helps ensure borrowers do not take on more housing debt or total debt than they can handle."
          }
        ]
      }
    ],
    finalQuiz: [
      {
        question: "What is rebalancing?",
        options: [
          "Selling all your investments",
          "Adjusting your portfolio back to your target allocation",
          "Only buying bonds",
          "Checking your balance"
        ],
        correct: 1,
        explanation: "Rebalancing means periodically adjusting your holdings to maintain your desired asset mix."
      },
      {
        question: "Which account type offers tax-free withdrawals in retirement?",
        options: [
          "Traditional IRA",
          "Regular brokerage account",
          "Roth IRA",
          "401(k)"
        ],
        correct: 2,
        explanation: "Roth IRA contributions are made with after-tax dollars, but qualified withdrawals are tax-free."
      },
      {
        question: "What should you do during a market crash?",
        options: [
          "Sell everything immediately",
          "Stay invested and possibly buy more if you have a long time horizon",
          "Check your portfolio every hour",
          "Move everything to cryptocurrency"
        ],
        correct: 1,
        explanation: "Staying invested through crashes and continuing to invest captures the recovery."
      },
      {
        question: "What is the three-fund portfolio?",
        options: [
          "Three individual stocks",
          "US stocks, international stocks, and bonds",
          "Three different brokerages",
          "A complex hedge fund strategy"
        ],
        correct: 1,
        explanation: "The three-fund portfolio is a simple, diversified approach using US stocks, international stocks, and bonds."
      },
      {
        question: "Why is a 1% expense ratio significant over 30 years?",
        options: [
          "It's not significant",
          "It can cost you 25% or more of your potential wealth due to compounding",
          "It only affects bonds",
          "Expense ratios are refundable"
        ],
        correct: 1,
        explanation: "Fees compound against you every year, significantly reducing your ending wealth over decades."
      }
    ]
  }
};

export default MODULES;
