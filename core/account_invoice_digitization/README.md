# Server requirements
Make sure you have the following pip packages installed in your Odoo server:

    pip3 install pytesseract pypdf pdf2image opencv-python

    apt update && apt install -y tesseract-ocr poppler-utils libgl1

### language packages for tesseract
Install language packs like this: apt install tesseract-ocr-lang
For example, to install French language pack:

    apt install tesseract-ocr-fra
 
#### available languages: https://github.com/tesseract-ocr/tesseract/blob/main/doc/tesseract.1.asc#languages
> afr (Afrikaans), amh (Amharic), ara (Arabic), asm (Assamese), aze (Azerbaijani), aze_cyrl (Azerbaijani - Cyrilic), bel (Belarusian), ben (Bengali), bod (Tibetan), bos (Bosnian), bre (Breton), bul (Bulgarian), cat (Catalan; Valencian), ceb (Cebuano), ces (Czech), chi_sim (Chinese simplified), chi_tra (Chinese traditional), chr (Cherokee), cos (Corsican), cym (Welsh), dan (Danish), deu (German), div (Dhivehi), dzo (Dzongkha), ell (Greek, Modern, 1453-), eng (English), enm (English, Middle, 1100-1500), epo (Esperanto), equ (Math / equation detection module), est (Estonian), eus (Basque), fas (Persian), fao (Faroese), fil (Filipino), fin (Finnish), fra (French), frk (Frankish), frm (French, Middle, ca.1400-1600), fry (West Frisian), gla (Scottish Gaelic), gle (Irish), glg (Galician), grc (Greek, Ancient, to 1453), guj (Gujarati), hat (Haitian; Haitian Creole), heb (Hebrew), hin (Hindi), hrv (Croatian), hun (Hungarian), hye (Armenian), iku (Inuktitut), ind (Indonesian), isl (Icelandic), ita (Italian), ita_old (Italian - Old), jav (Javanese), jpn (Japanese), kan (Kannada), kat (Georgian), kat_old (Georgian - Old), kaz (Kazakh), khm (Central Khmer), kir (Kirghiz; Kyrgyz), kmr (Kurdish Kurmanji), kor (Korean), kor_vert (Korean vertical), lao (Lao), lat (Latin), lav (Latvian), lit (Lithuanian), ltz (Luxembourgish), mal (Malayalam), mar (Marathi), mkd (Macedonian), mlt (Maltese), mon (Mongolian), mri (Maori), msa (Malay), mya (Burmese), nep (Nepali), nld (Dutch; Flemish), nor (Norwegian), oci (Occitan post 1500), ori (Oriya), osd (Orientation and script detection module), pan (Panjabi; Punjabi), pol (Polish), por (Portuguese), pus (Pushto; Pashto), que (Quechua), ron (Romanian; Moldavian; Moldovan), rus (Russian), san (Sanskrit), sin (Sinhala; Sinhalese), slk (Slovak), slv (Slovenian), snd (Sindhi), spa (Spanish; Castilian), spa_old (Spanish; Castilian - Old), sqi (Albanian), srp (Serbian), srp_latn (Serbian - Latin), sun (Sundanese), swa (Swahili), swe (Swedish), syr (Syriac), tam (Tamil), tat (Tatar), tel (Telugu), tgk (Tajik), tha (Thai), tir (Tigrinya), ton (Tonga), tur (Turkish), uig (Uighur; Uyghur), ukr (Ukrainian), urd (Urdu), uzb (Uzbek), uzb_cyrl (Uzbek - Cyrilic), vie (Vietnamese), yid (Yiddish), yor (Yoruba)