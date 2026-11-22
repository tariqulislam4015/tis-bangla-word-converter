"""Reference corpus: Unicode input -> expected Bijoy (SutonnyMJ) output.

Expected values follow the standard Bijoy/SutonnyMJ forms used in Bangladeshi
publishing.  Entries are grouped by the feature they exercise.
"""

VOWELS = [
    ("অ আ ই ঈ উ ঊ ঋ এ ঐ ও ঔ", "A Av B C D E F G H I J"),
    ("আমি", "Avwg"),
    ("ঐক্য", "HK¨"),
    ("উৎসব", "Drme"),
]

CONSONANTS = [
    ("ক খ গ ঘ ঙ", "K L M N O"),
    ("চ ছ জ ঝ ঞ", "P Q R S T"),
    ("ট ঠ ড ঢ ণ", "U V W X Y"),
    ("ত থ দ ধ ন", "Z _ ` a b"),
    ("প ফ ব ভ ম", "c d e f g"),
    ("য র ল শ ষ স হ", "h i j k l m n"),
    ("ড় ঢ় য় ৎ", "o p q r"),
]

KARS = [
    ("কা কি কী কু কূ কৃ কে কৈ কো কৌ", "Kv wK Kx Kz K‚ K… †K ˆK †Kv †KŠ"),
    ("পা পি পী পু পূ পৃ", "cv wc cx cy c~ c„"),
    ("তুমি", "Zzwg"),
    ("ভূমি", "f‚wg"),
    ("পৃথিবী", "c„w_ex"),
    ("বাংলাদেশ", "evsjv‡`k"),
    ("আমার সোনার বাংলা", "Avgvi †mvbvi evsjv"),
    ("বৈশাখ", "ˆekvL"),
    ("কৌশল", "†KŠkj"),
    ("গুরু", "¸iæ"),
    ("শুভ", "ïf"),
    ("হৃদয়", "ü`q"),
    ("হুকুম", "ûKzg"),
]

SIGNS = [
    ("চাঁদ", "Pvu`"),
    ("দুঃখ", "`ytL"),
    ("ইংরেজি", "Bs‡iwR"),
    ("পিঁপড়া", "wcucov"),
]

CONJUNCTS = [
    ("শিক্ষা", "wk¶v"),
    ("ক্ষুদ্র", "ÿz`ª"),
    ("বিজ্ঞান", "weÁvb"),
    ("কিন্তু", "wKš‘"),
    ("উজ্জ্বল", "D¾¡j"),
    ("তত্ত্ব", "ZË¡"),
    ("লক্ষ্মী", "j²x"),
    ("সূক্ষ্ম", "m~²"),
    ("তীক্ষ্ণ", "Zx¶è"),
    ("সংস্কৃতি", "ms¯‹…wZ"),
    ("স্কুল", "¯‹yj"),
    ("যন্ত্র", "hš¿"),
    ("স্ত্রী", "¯¿x"),
    ("মেরুদণ্ড", "†giæ`Ð"),
    ("অবশ্যম্ভাবী", "Aek¨¤¢vex"),
    ("বিচ্ছেদ", "we‡”Q`"),
    ("নিষ্ঠা", "wbôv"),
    ("কষ্ট", "Kó"),
    ("সম্পর্ক", "m¤úK©"),
    ("বুদ্ধি", "eyw×"),
    ("পদ্ম", "cÙ"),
    ("অঙ্ক", "A¼"),
    ("বঙ্গ", "e½"),
]

REPH = [
    ("কর্ম", "Kg©"),
    ("ধর্মে", "a‡g©"),
    ("ধর্মীয়", "ag©xq"),
    ("নির্বাচন", "wbe©vPb"),
    ("কীর্তি", "KxwZ©"),
    ("কার্যালয়", "Kvh©vjq"),
    ("সূর্য", "m~h©"),
    ("আর্দ্র", "Av`ª©"),
    ("কর্তৃক", "KZ©„K"),
    ("মুহূর্ত", "gyn~Z©"),
    ("জ্ঞানার্জনের", "ÁvbvR©‡bi"),
    ("ধৈর্য", "ˆah©"),
    ("দৈর্ঘ্য", "ˆ`N©¨"),
    ("সামর্থ্য", "mvg_©¨"),
]

R_PHALA = [
    ("প্রশ্ন", "cÖkœ"),
    ("গ্রাম", "MÖvg"),
    ("প্রতি", "cÖwZ"),
    ("রাষ্ট্র", "ivóª"),
    ("চন্দ্র", "P›`ª"),
    ("দ্রুত", "`ªæZ"),
    ("শত্রু", "kÎæ"),
    ("ট্রাক", "UªvK"),
    ("ফ্রিজ", "wd«R"),
    ("হ্রদ", "n«`"),
    ("ক্রয়", "µq"),
    ("ভ্রমণ", "ågY"),
    ("শ্রদ্ধা", "kÖ×v"),
]

YA_PHALA = [
    ("ব্যাংক", "e¨vsK"),
    ("মৃত্যু", "g„Zz¨"),
    ("বিশ্ববিদ্যালয়", "wek¦we`¨vjq"),
    ("অ্যাসিড", "A¨vwmW"),
    ("র‍্যাব", "i¨ve"),
    ("প্রত্যেকেই", "cÖ‡Z¨‡KB"),
    ("মাধ্যমে", "gva¨‡g"),
]

B_PHALA = [
    ("স্বাধীনতা", "¯^vaxbZv"),
    ("বিশ্ব", "wek¦"),
    ("দ্বিতীয়", "wØZxq"),
    ("জ্বর", "R¡i"),
]

NUMBERS_PUNCT = [
    ("০১২৩৪৫৬৭৮৯", "0123456789"),
    ("২০২৪ সাল", "2024 mvj"),
    ("প্রশ্ন: ১। কোনটি সঠিক?", "cÖkœ: 1| †KvbwU mwVK?"),
    ("“আমি”", "ÒAvwgÓ"),
    ("‘না’", "ÔbvÕ"),
    ("বাংলা—ভাষা", "evsjvÑfvlv"),
]

MIXED = [
    ("Hello বাংলা world", "Hello evsjv world"),
    ("x + ২ = ৫", "x + 2 = 5"),
    ("ক্লাস 8 (Science)", "K¬vm 8 (Science)"),
    ("a² + b² = c²", "a² + b² = c²"),
    ("email: test@example.com", "email: test@example.com"),
]

SENTENCES = [
    ("জ্ঞানার্জনের পথটি কষ্টসাধ্য হলেও অবিচ্ছেদ্য সাধনা এবং নিষ্ঠার মাধ্যমে তা সফল হতে পারে।",
     "ÁvbvR©‡bi c_wU Kómva¨ n‡jI Awe‡”Q`¨ mvabv Ges wbôvi gva¨‡g Zv mdj n‡Z cv‡i|"),
    ("আমাদের প্রত্যেকেই যেন উদ্যম ও ধৈর্য সহকারে জীবনের বিভিন্ন ক্ষেত্রে জয় করি",
     "Avgv‡`i cÖ‡Z¨‡KB †hb D`¨g I ˆah© mnKv‡i Rxe‡bi wewfbœ †¶‡Î Rq Kwi"),
    ("আমরা চেষ্টা করলে অবশ্যই অগ্রসর হতে পারব।",
     "Avgiv †Póv Ki‡j Aek¨B AMÖmi n‡Z cvie|"),
]

ALL = (VOWELS + CONSONANTS + KARS + SIGNS + CONJUNCTS + REPH + R_PHALA
       + YA_PHALA + B_PHALA + NUMBERS_PUNCT + MIXED + SENTENCES)

# Bengali-only entries are expected to survive Bijoy -> Unicode round trip.
ROUND_TRIP = [u for u, _ in ALL if not any(c.isascii() and c.isalpha() for c in u)
              and "²" not in u]
