# Style Guide

Use these presets to produce original WeChat comic long images with repeatable visual language. Match broad format and reading experience only; never copy account identity, author signature, fixed characters, or branded phrases.

## 风格一：白底科普漫画

- Canvas: 600px wide, white background.
- Layout: centered title, short centered paragraphs, image/text alternation, generous whitespace. Prefer moderate-height panels: source image `2304x1728` (4:3), displayed at `520-540px` wide. Avoid tall panels that occupy a full phone screen.
- Art: original educational comic with finished public-account illustration quality. Use clean ink lines, restrained warm color or clean black-and-white line art, soft white/pastel space, and gentle readable expressions. Characters must be anatomically coherent, not merely "human-shaped". Generated panel art must contain no written text.
- Text: conversational science or life explanation, one clear idea per block. For short centered lines, remove decorative sentence-ending punctuation such as `，` `。` `；` `：`; keep `？` only when the line is genuinely a question.
- Prompt key: "standalone Chinese public-account editorial illustration, finished polished illustration quality, clean black ink linework, restrained warm colors or clean black-and-white line art, soft white or pastel background, clear central subject, gentle expressive characters, anatomically coherent complete human figures, one head per person, clear face neck torso arms hands legs feet, natural joints, natural posture, correct scale relationships, emotionally readable expressions, simple uncluttered mobile-readable composition, purely visual illustration, absolutely no written language anywhere, no Chinese characters, no English letters, no numbers, no captions, no speech bubbles, no comic sound effects, no title text, no handwriting, no labels, no poster text, no UI text, all screens books clocks papers signs whiteboards posters and product surfaces must be blank or abstract, no watermark, no logo, no rough storyboard, no messy pencil draft, no dirty gray shading, no distorted faces, no duplicate heads, no floating facial parts, no detached hair, no extra limbs, no missing limbs, no fused bodies, no broken hands, no backward joints, no stick figures, no bean bodies, no blob people, no pictogram icons".
- Template: `templates/article-template.json`.

## 风格二：蓝条心理叙事

- Canvas: about 700px wide, white background.
- Layout: soft full-width image opening, stacked blue text bars, occasional yellow words in blue bars, red thesis emphasis, then repeated narrator/dialogue panels.
- Art: soft psychological WeChat longform comic illustration, warm sunlight, cozy counseling interiors, gentle outdoor metaphors, clean but not glossy hand-drawn manga line art, slightly thicker black outlines, flat warm colors with light watercolor wash, soft white faded edges. Recurring characters can include a calm Chinese female psychological consultant with straight black shoulder-length hair and mustard cardigan or light blazer, plus a Chinese female client with long black hair, white shirt, and muted green vest or dress. Metaphor panels may use simple faceless cream-colored mascot figures and symbolic objects instead of recurring people. Generated panels are wordless; blue narration bars and article text are added by the layout script.
- Text: relationship, psychology, growth, life-choice topics. Sentences should be short and declarative. Use blue bars as the main body text, not decorative captions.
- Blocks: use `text_bars` for most narration, `emphasis` for red conclusion lines, `image` with `fade_edges` for soft image transitions.
- Prompt key: "WORDLESS IMAGE ONLY, soft psychological WeChat longform comic illustration panel, portrait-oriented scene, clean but not glossy hand-drawn manga line art, slightly thicker black outlines, simple elegant adult facial features, restrained proportions, flat warm colors with light watercolor wash, white glow fade at top and bottom edges, when people are needed use a calm Chinese female psychological consultant with straight black shoulder-length hair and mustard cardigan or light blazer over cream turtleneck, or a Chinese female client with long black hair, white shirt and muted green vest or green dress, for metaphor scenes simple faceless cream-colored mascot figures paths flowers phones cups windows and symbolic objects are allowed, warm sunlight, cozy counseling room, yellow sofa, plants, books, desk, bed, cup, vase, bright window, gentle outdoor metaphors, soft golden-beige palette, quiet relationship-healing mood, emotional but restrained expressions, no glossy high-detail anime rendering, no cinematic photorealism, no over-rendered skin, no childlike cute style, no generated written language, no Chinese characters, no English letters, no numbers, no captions, no labels, no UI text, no blue text bars, no colored text strips, no logo, no watermark".

## 风格三：绿底职场对比

- Canvas: about 690px wide, muted green background with subtle diagonal texture.
- Layout: opening illustrated intro, numbered section labels, black rounded `framed_image` panels, each section compares two time states such as "上班第一年" and "上班第五年".
- Art: WeChat workplace comparison comic, portrait-oriented scenes, rough thick black hand-drawn outlines, lightly wobbly ink, flat color blocks with subtle paper-grain texture, busy modern office details, expressive young workers, controlled saturated palette, recurring young Chinese woman employee with light-brown shoulder-length hair, compatible with black rounded frames and green background.
- Text: direct workplace observations. In-panel title bars, speech bubbles, chat boxes, timestamps, sound effects, and emphasized words are generated by Seedream directly. Every string to render must be wrapped in quotation marks in the panel prompt.
- Blocks: use `section_label`, `framed_image`, and short `paragraph` or `section_label` takeaways with stroke. Avoid `speech_bubbles` overlays for `风格三` unless repairing a failed generated panel manually.
- Prompt key: "WeChat public-account workplace comparison comic panel with AI-rendered Chinese text, portrait-oriented office scene, rough thick black hand-drawn outlines, lightly wobbly ink edges, flat color blocks, subtle paper grain texture, simplified expressive adult Chinese office workers, recurring young Chinese woman employee with light-brown shoulder-length hair, green top or vest, white striped sleeves, brown jacket, blue pants, work badge, desks, laptops, documents, coffee mugs, plants, night city windows, sunset windows, office lights, readable foreground action, compact dramatic composition, black rounded panel frame, green article-compatible border, render only the exact Chinese text explicitly wrapped in quote marks in the scene prompt, copy quoted Chinese exactly without rewriting or shortening, put quoted dialogue inside white speech bubbles with black outlines, put quoted section/header text in a black top title bar with white characters, put quoted phone/chat messages inside white rectangular message boxes, quoted text must be large and mobile-readable, no extra Chinese characters, no English letters, no pinyin, no random labels, no UI text, no poster text, no background wall text, no watermark, no logo, no signature, no childlike cute style, no messy sketch, no watercolor softness, no photorealism, no glossy anime, no malformed bodies".

## Review Checklist

- First viewport should immediately read as the requested style.
- Deterministic text must be readable on mobile.
- Short centered Chinese lines should not end with unnecessary punctuation marks.
- Generated panels must not contain garbled Chinese.
- 风格一图片必须像完成稿：出现人物怪脸、多头、头发/五官漂浮、肢体畸形、多人融合、手脚错误、脏灰草稿感、画风前后漂移时必须重生成。
- 风格一图片内不能有任何文字、数字、标题、拟声词、气泡文字、标签、屏幕文字或招牌文字；出现就重生成。
- Reuse no named author, brand, fixed character identity, account banner, or signature.
- If a generated panel drifts, adjust prompt first; if text rhythm drifts, adjust JSON blocks.
