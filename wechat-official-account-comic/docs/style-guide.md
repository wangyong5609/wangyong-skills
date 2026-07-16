# Style Guide

Use these presets to produce original WeChat comic long images with repeatable visual language. Match broad format and reading experience only; never copy account identity, author signature, fixed characters, or branded phrases.

## Contents

- 暖白手绘漫画
- 蓝栏柔彩漫画
- 绿底粗线漫画
- 小林诗意治愈
- 小林生活讽刺
- 小林奇想涂鸦
- 小林三风格公共生产规则
- Review checklist

For styles trained from new reference screenshots, read `style-training-guide.md`, create a profile from `templates/style-profile-template.json`, and save it as `styles/<style-id>.json`. Add only a concise entry here after the style has a reusable prompt, layout notes, text policy, and quality gate.

## 暖白手绘漫画

- Canvas: 600px wide, white background.
- Layout: starts from opening body copy, then short centered paragraphs, image/text alternation, generous whitespace. The WeChat article title stays outside the long image. Prefer moderate-height panels: source image `2304x1728` (4:3), displayed at `520-540px` wide. Avoid tall panels that occupy a full phone screen.
- Art: original educational comic with finished public-account illustration quality. Use clean ink lines, restrained warm color or clean black-and-white line art, soft white/pastel space, and gentle readable expressions. Characters must be anatomically coherent, not merely "human-shaped". Generated panel art must contain no written text.
- Text: conversational science or life explanation, one clear idea per block. For short centered lines, remove decorative sentence-ending punctuation such as `，` `。` `；` `：`; keep `？` only when the line is genuinely a question.
- Text policy: `wordless`.
- Prompt key: load `styles/warm-white-handdrawn.json` and append its `style_prompt` to every panel prompt.
- Template: `templates/article-template.json`. Style profile: `styles/warm-white-handdrawn.json`.

## 蓝栏柔彩漫画

- Canvas: about 700px wide, white background.
- Layout: soft full-width image opening, stacked blue text bars, occasional yellow words in blue bars, red thesis emphasis, then repeated narrator/dialogue panels.
- Art: soft psychological WeChat longform comic illustration, warm sunlight, cozy counseling interiors, gentle outdoor metaphors, clean but not glossy hand-drawn manga line art, slightly thicker black outlines, flat warm colors with light watercolor wash, soft white faded edges. Recurring characters can include a calm Chinese female psychological consultant with straight black shoulder-length hair and mustard cardigan or light blazer, plus a Chinese female client with long black hair, white shirt, and muted green vest or dress. Metaphor panels may use simple faceless cream-colored mascot figures and symbolic objects instead of recurring people. Generated panels are wordless; blue narration bars and article text are added by the layout script.
- Text: relationship, psychology, growth, life-choice topics. Sentences should be short and declarative. Use blue bars as the main body text, not decorative captions.
- Blocks: use `text_bars` for most narration, `emphasis` for red conclusion lines, `image` with `fade_edges` for soft image transitions.
- Text policy: `wordless`.
- Prompt key: load `styles/blue-bar-soft-color.json` and append its `style_prompt` to every panel prompt.
- Template: `templates/article-template-blue-bar-soft-color.json`. Style profile: `styles/blue-bar-soft-color.json`.

## 绿底粗线漫画

- Canvas: about 690px wide, muted green background with subtle diagonal texture.
- Layout: opening illustrated intro, numbered section labels, black rounded `framed_image` panels, each section compares two time states such as "上班第一年" and "上班第五年".
- Art: WeChat workplace comparison comic, portrait-oriented scenes, rough thick black hand-drawn outlines, lightly wobbly ink, flat color blocks with subtle paper-grain texture, busy modern office details, expressive young workers, controlled saturated palette, recurring young Chinese woman employee with light-brown shoulder-length hair, compatible with black rounded frames and green background.
- Text policy: `model-rendered`. In-panel title bars, speech bubbles, chat boxes, timestamps, sound effects, and emphasized words are generated directly by the image model. Every string to render must be wrapped in quotation marks in the panel prompt.
- Blocks: use `section_label`, `framed_image`, and short `paragraph` or `section_label` takeaways with stroke. Do not use deterministic `speech_bubbles` or `framed_image.header` overlays for this style.
- Prompt key: load `styles/green-bold-line.json` and append its `style_prompt` to every panel prompt.
- Template: `templates/article-template-green-bold-line.json`. Style profile: `styles/green-bold-line.json`.

## 小林诗意治愈：白底水彩治愈

- Canvas: 600px wide, white background, tall vertical long image with generous whitespace.
- Aliases: `小林诗意治愈`, `小林水彩治愈`, `小林风格`, `小林风格1`, `小林漫画1`, `小林治愈`, `xiaolin-healing`, `xiaolin-style`.
- Layout: starts with the first centered small red `badge` number, then one complete source image. Each source image contains the watercolor illustration in the upper area and the handwritten Chinese caption in the lower area. Repeat 3-6 times. Do not include the WeChat article title, WeChat app chrome, QR codes, signatures, account names, or account metadata in the final comic.
- Art: original soft watercolor illustration with loose black ink linework, transparent washes, visible paper texture, natural metaphors, and quiet emotional scenes. Use simple subjects such as balloons, trees, grass, mountains, fields, cottages, rain, flowers, windows, or tiny solitary people. Keep scenes gentle and sparse, with the caption area clearly separated below.
- Text policy: `model-rendered`. The caption is generated inside the source image, not added later by the layout script. Put every caption line in double quotation marks in the prompt, and ask the model to render only those quoted Chinese strings.
- Caption lettering: describe it as large black handwritten Chinese brush lettering, dense ink, uneven thick-and-thin strokes, rough dry-brush edges, organic imperfect character shapes, centered 2-4 lines, generous line spacing. It is not a known local font; do not ask for Songti, Heiti, Kaiti, PingFang, typed subtitle text, or clean vector calligraphy.
- Copy: short poetic affirmations, usually 2-4 lines, 8-14 Chinese characters per line, minimal punctuation. The caption should feel like a human hand wrote it with a soft brush or dark ink marker.
- Blocks: use `badge` and `image`. Do not use `brush_text` for normal 小林 production because the source image already contains the caption. Template: `templates/article-template-xiaolin-style.json`. Style profile: `styles/xiaolin-healing.json`.
- Generation mode: prompt-only by default after training. Do not attach the original screenshot as a reference image unless the user is explicitly re-training or comparing style drift.
- Prompt key: load `styles/xiaolin-healing.json` and append its `style_prompt` to every panel prompt.
- Prompt-only test result: a no-reference Agent imagegen prompt with a tree scene, one seated person, and the quoted lines `"人这一生"`, `"自私很容易"`, `"爱自己却很难"` produced a single source image containing both the watercolor illustration and the lower handwritten caption. The accepted result had legible three-line black brush lettering and no QR code, signature, account name, or extra text. This confirms normal production should be prompt-only after the style profile exists.
- Prompt recipe: say `complete source image as one bitmap`; specify upper illustration area and lower caption area; include a `Text to render exactly` block with each caption line in double quotation marks; describe typography as black handwritten brush lettering; forbid QR codes, watermarks, logos, signatures, account names, English, random numbers, and unquoted text.
- Iteration note: the tested output can become cleaner, taller, or fuller than the rougher reference. When this drift appears, add `smaller watercolor mass`, `more white paper margin`, `looser uneven watercolor wash`, `rougher hand-painted paper texture`, and `less polished rendering`. Text accuracy still needs manual QA; wrong or garbled characters require regeneration.

## 小林生活讽刺：生活讽刺小品

- Canvas: 600px wide, white background, tall vertical long image with large white-space gaps.
- Aliases: `小林风格2`, `小林漫画2`, `小林生活观察`, `小林生活讽刺`, `xiaolin-life-satire`.
- Layout: starts with the first centered small red `badge` number, then one complete source image. Each source image contains a rough watercolor caricature life scene in the upper or middle area and the handwritten Chinese caption in the lower area. Repeat 5-8 times. Do not include the WeChat article title, WeChat app chrome, QR codes, signatures, account names, side marks, or account metadata in the final comic.
- Art: original loose watercolor caricature with rough black-brown ink lines, slightly dirty hand-painted texture, low-saturation washes, and ordinary Chinese life scenes. Use expressive but complete people: tired middle-aged adults, elders, parents, children, office workers, small shop owners, doctors, neighbors, or commuters. Favor awkward poses, red noses, wrinkled brows, slumped shoulders, sofas, dining tables, office desks, bills, phones, buildings, buses, beds, card tables, and daily objects. Keep it human, funny, and a little sharp; avoid polished anime, healing landscape posters, photorealism, 3D, or copied fixed characters.
- Text policy: `model-rendered`. The punchline caption is generated inside the source image, not added later by the layout script. Put every caption line in double quotation marks in the prompt, and ask the model to render only those quoted Chinese strings.
- Caption lettering: describe it as large black handwritten Chinese brush or marker lettering, dense ink, uneven thick-and-thin strokes, rough dry-brush edges, organic imperfect character shapes, centered 2-5 lines, generous line spacing. It should not look like Songti, Heiti, Kaiti, PingFang, typed subtitle text, or clean vector calligraphy.
- Copy: life observation, family/workplace pressure, middle-age fatigue, social humor, and ironic comfort. Usually 2-5 lines, 8-18 Chinese characters per line. Rhythm: ordinary scene -> reversal -> understated punchline. Keep the wording original; do not reuse reference captions.
- Blocks: use `badge` and `image`. Do not use `brush_text` for normal 小林 production because the source image already contains the caption. Template: `templates/article-template-xiaolin-life-satire.json`. Style profile: `styles/xiaolin-life-satire.json`.
- Generation mode: prompt-only by default after training. Do not attach the original screenshot as a reference image unless the user is explicitly re-training or comparing style drift.
- Prompt key: load `styles/xiaolin-life-satire.json` and append its `style_prompt` to every panel prompt.
- Validation note: this profile was added from reference analysis of the provided life-observation screenshot. A prompt-only image smoke test has not yet been recorded; run one 1-2 panel test before full production and record whether the text, rough caricature look, and no-brand constraints pass.
- Prompt recipe: say `complete source image as one bitmap`; specify upper or middle rough watercolor caricature scene and lower caption area; include a `Text to render exactly` block with each caption line in double quotation marks; describe typography as black handwritten brush or marker lettering; forbid QR codes, watermarks, logos, signatures, account names, English, random numbers, and unquoted text.
- Iteration note: if the result drifts into the softer healing style, add ordinary people, daily props, awkward posture, rougher black-brown linework, lower-saturation dirty watercolor, and a sharper satirical punchline. If text is inaccurate, regenerate the panel instead of accepting it.

## 小林奇想涂鸦：奇想涂鸦哲思

- Canvas: 600px wide, white background, tall vertical long image with generous whitespace.
- Aliases: `小林风格3`, `小林漫画3`, `小林奇想`, `小林奇想涂鸦`, `小林脑洞哲思`, `xiaolin-whimsy-doodle`.
- Layout: starts with the first centered small red `badge` number, then one complete source image. Each source image contains a small playful watercolor doodle in the upper or middle area and the handwritten Chinese caption in the lower area. Repeat 6-10 times. Do not include the WeChat article title, WeChat app chrome, QR codes, signatures, account names, side marks, or account metadata in the final comic.
- Art: original whimsical doodles with loose black marker/ink lines, simple rounded shapes, transparent watercolor or flat-color washes, and frequent small colored square backgrounds. Use cute animals, odd little monsters, personified objects, cats, ducks, fish, hedgehogs, dinosaurs, cups, books, plants, clouds, food, buses, beds, or tiny ordinary people as metaphors. Keep the drawing light, small, blank-space-heavy, and slightly absurd. Avoid realistic adult-pressure scenes, polished anime, dense backgrounds, photorealism, 3D, copied fixed characters, or pure nature landscape posters.
- Text policy: `model-rendered`. The philosophical or humorous caption is generated inside the source image, not added later by the layout script. Put every caption line in double quotation marks in the prompt, and ask the model to render only those quoted Chinese strings.
- Caption lettering: describe it as large black handwritten Chinese brush or marker lettering, dense ink, uneven thick-and-thin strokes, rough dry-brush edges, organic rounded character shapes, centered 2-5 lines, generous line spacing. It should not look like Songti, Heiti, Kaiti, PingFang, typed subtitle text, or clean vector calligraphy.
- Copy: gentle absurdity, cute-object metaphor, self-comfort, small social observation, and light philosophical one-liners. Usually 2-5 lines, 7-16 Chinese characters per line. Rhythm: small visual metaphor -> everyday feeling -> quiet twist. Keep the wording original; do not reuse reference captions.
- Blocks: use `badge` and `image`. Do not use `brush_text` for normal 小林 production because the source image already contains the caption. Template: `templates/article-template-xiaolin-whimsy-doodle.json`. Style profile: `styles/xiaolin-whimsy-doodle.json`.
- Generation mode: prompt-only by default after training. Do not attach the original screenshot as a reference image unless the user is explicitly re-training or comparing style drift.
- Prompt key: load `styles/xiaolin-whimsy-doodle.json` and append its `style_prompt` to every panel prompt.
- Validation note: this profile was added from reference analysis of three provided screenshots and then tested with an 8-panel prompt-only long image at `output/comics/越长大越想把日子过轻一点/越长大越想把日子过轻一点-小林风格3测试长图.png`. The test kept QR/signature/account artifacts out and produced usable handwritten captions after regenerating one failed panel.
- Prompt recipe: say `complete source image as one bitmap`; specify upper or middle small whimsical doodle scene and lower caption area; include a `Text to render exactly` block with each caption line in double quotation marks; describe typography as black handwritten brush or marker lettering; forbid QR codes, watermarks, logos, signatures, account names, English, random numbers, and unquoted text.
- Iteration note: if the output becomes too similar to `小林诗意治愈`, add cute animal/object absurdity and a sharper conceptual twist. If it becomes too similar to `小林生活讽刺`, remove office/adult-pressure realism and switch to animals, odd objects, tiny monsters, or colored wash squares. If text is inaccurate, shorten the caption lines and regenerate the panel instead of accepting it. If sleeping scenes add `Z`/`zzz`, explicitly forbid sleep letters, sound effects, labels, symbols, and speech bubbles.

## 小林三风格公共生产规则

- `小林诗意治愈`, `小林生活讽刺`, and `小林奇想涂鸦` all use the same independent quote-and-metaphor workflow. They are not continuous story comics; every numbered image must be understandable as a standalone caption-and-visual-metaphor unit under the same topic.
- The Agent must follow the confirmation sequence in `docs/comic-creator-workflow.md`: 主题/风格确认 -> 金句组确认 -> prompt 确认 -> 图片验收 -> final layout. Do not generate prompts before 金句组确认, do not generate images before prompt 确认, and do not stitch the long image before 图片验收 passes for every panel.
- The approved beat table is the production source of truth. Captions, visual metaphors, image prompts, generated panel filenames, `badge` numbers, and final layout order should all use that same numbered sequence.
- The default final order is the approved beat order. Reorder only when the user explicitly asks, then keep the revised order consistent across prompts, filenames, badges, and `article.json`.

## Review Checklist

- First viewport should immediately read as the requested style.
- For trained styles, `styles/<style-id>.json` must include `name`, `style_prompt`, and `text_policy`; `wordless` profiles must keep all Chinese text out of generated images, while `model-rendered` profiles must render only quoted Chinese strings.
- 小林系风格必须把双引号内 caption 生成在源图下半部分，字形像黑色手写毛笔字/马克笔字；不得出现二维码、署名、账号名、参考图固定文案、乱码或任何未被引号包住的额外文字。
- 小林风格选择边界：`小林诗意治愈` 偏自然/治愈/诗意；`小林生活讽刺` 偏普通人生活压力/讽刺小品；`小林奇想涂鸦` 偏可爱动物、怪物、拟人化物件和脑洞哲思。数字别名 `小林风格1/2/3` 只用于兼容旧说法。选错会导致画面语气漂移。
- 小林奇想涂鸦的常见失败是画面太满、人物太现实、主题太职场、文字太工整、或者变成纯风景治愈图；出现这些问题时，用更小主体、更多白纸、可爱物象、彩色水彩方块和轻荒诞转折重写 prompt。
- Deterministic text must be readable on mobile.
- The WeChat article title must not appear inside the final long image or any generated panel.
- Short centered Chinese lines should not end with unnecessary punctuation marks.
- Generated panels must not contain garbled Chinese.
- 暖白手绘漫画图片必须像完成稿：出现人物怪脸、多头、头发/五官漂浮、肢体畸形、多人融合、手脚错误、脏灰草稿感、画风前后漂移时必须重生成。
- 暖白手绘漫画图片内不能有任何文字、数字、标题、拟声词、气泡文字、标签、屏幕文字或招牌文字；出现就重生成。
- Reuse no named author, brand, fixed character identity, account banner, or signature.
- If a generated panel drifts, adjust prompt first; if text rhythm drifts, adjust JSON blocks.
