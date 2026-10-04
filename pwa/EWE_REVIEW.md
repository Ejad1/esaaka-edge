# Ewe review sheet (MACHINE-TRANSLATED DRAFT, NOT VALIDATED)

Main draft: Google Translate FR->EE. `Alt` = independent EN->EE. `Back` = EE->FR to check the meaning. `Agree` is string similarity between the two Ewe versions (low = suspicious). Correct `src/i18n/ee.json` where wrong.

| key | French | Ewe draft (shipped) | Ewe alt (EN->EE) | agree | back to French | placeholders ok |
|---|---|---|---|---|---|---|
| `app_name` | Esaaka Edge | Esaaka Edge ƒe ŋkɔ | Esaaka Edge ƒe ŋkɔ | 1.00 | Nom d'Esaaka Edge | yes |
| `tagline` | Je regarde une feuille de caféier, même sans internet. | Meléa ŋku ɖe kɔfi aŋgba aɖe ŋu, internet manɔmee gɔ̃ hã. | Meléa ŋku ɖe kɔfi aŋgba aɖe ŋu, internet manɔmee gɔ̃ hã. | 1.00 | Je regarde une feuille de café, même sans Internet. | yes |
| `works_offline` | Fonctionne sans internet | Ewɔa dɔ internet manɔmee | Ewɔa dɔ le Internet dzi | 0.72 | Cela fonctionne sans Internet | yes |
| `online` | En ligne | Le kadzi | Le kadzi | 1.00 | En ligne | yes |
| `offline` | Hors ligne | Le Internet dzi | Le Internet dzi | 1.00 | Sur Internet | yes |
| `take_photo` | Prendre une photo | Ðe foto | Ðe foto | 1.00 | Prendre une photo | yes |
| `choose_photo` | Choisir une photo | Tia foto aɖe | Tia foto aɖe | 1.00 | Sélectionnez une photo | yes |
| `my_obs` | Mes observations | Nye ŋkuléleɖenuŋu | Nye ŋkuléleɖenuŋu | 1.00 | Mon observation | yes |
| `home` | Accueil | Woezɔ̃ | Aƒeme | 0.18 | Accueillir | yes |
| `protocol_title` | Pour une bonne photo | Ne èdi foto nyui aɖe | Ne èdi foto nyui aɖe | 1.00 | Si tu veux une bonne photo | yes |
| `protocol_1` | Cueillez une feuille et posez-la sur une surface unie (papier, tissu clair). | Tia agbalẽ aɖe eye nàtsɔe aɖo teƒe gbadza aɖe (pepa, avɔ si me kɔ). | Tia aŋgba ɖeka eye nàtsɔe aɖo anyigba gbadza dzi (pepa, avɔ si me kɔ). | 0.83 | Choisissez une feuille et placez-la sur une surface plane (papier, tissu léger). | yes |
| `protocol_2` | Une seule feuille, bien éclairée, sans ombre forte, qui remplit la largeur. | Agba ɖeka, si me kekeli le nyuie, si me vɔvɔli sesẽ aɖeke mele o, si yɔa kekeme. | Agba ɖeka, si me kekeli le nyuie, vɔvɔli sesẽ aɖeke mele eŋu o, si yɔ fotoa ƒe kekeme. | 0.89 | Feuille unique, bien éclairée, sans ombres dures, remplissant l'espace. | yes |
| `protocol_3` | Tenez le téléphone sans bouger pour que la photo soit nette. | Lé telefon la ɖe asi evɔ màʋuʋu o ale be fotoa me nakɔ. | Lé telefon la ɖe asi sesĩe ale be fotoa nadze nyuie. | 0.75 | Tenez le téléphone sans bouger pour que la photo soit nette. | yes |
| `analyzing` | Analyse sur ce téléphone… | Analysis le telefon sia dzi... | Analysing le telefon sia dzi... | 0.95 | Analyse sur ce téléphone… | yes |
| `retake` | Reprendre la photo | Gbugbɔ dze fotoa gɔme | Gbugbɔ ɖe fotoa | 0.78 | Redémarrez la photo | yes |
| `saved_on_device` | Enregistré sur ce téléphone | Wodzrae ɖo ɖe telefon sia dzi | Wodzrae ɖo ɖe telefon sia dzi | 1.00 | Enregistré sur ce téléphone | yes |
| `ask_officer` | Demander à l'agent de vulgarisation | Bia kekeɖenudɔdzikpɔla la | Bia kekeɖenudɔdzikpɔla la | 1.00 | Demandez à l'agent de vulgarisation | yes |
| `back` | Retour | Megbe | Megbe | 1.00 | Dos | yes |
| `guard_title` | Photo à reprendre | Foto si woagaɖe ake | Taflatse gbugbɔ ɖe fotoa | 0.23 | Une photo à reprendre | yes |
| `guard_intro` | Je ne donne pas de diagnostic sur cette photo, car : | Menye ɖe mele dɔléle ŋuti nyatakaka aɖe nam le foto sia me o, elabena: | Nyemagblɔ dɔléle ŋuti nyatakaka aɖeke le foto sia ŋu o, elabena: | 0.84 | Je ne fais pas de constat pathologique sur cette photo, car : | yes |
| `guard_blur` | elle est floue | eƒe nu me mekɔ o | eƒe nu me mekɔ o | 1.00 | sa bouche n'était pas claire | yes |
| `guard_too_dark` | elle est trop sombre | eƒe viviti do akpa | viviti do akpa | 0.88 | il fait trop sombre | yes |
| `guard_too_bright` | elle est trop claire | eƒe nu me kɔ akpa | eklẽna akpa | 0.50 | c'est trop brillant | yes |
| `guard_low_contrast` | elle manque de contraste | vovototo aɖeke mele eme o | vovototo boo aɖeke mele eme o | 0.93 | il n'y a pas de différence | yes |
| `guard_busy_background` | le fond est trop chargé : posez la feuille sur une surface unie | megbenyawo sɔ gbɔ akpa: da agbalẽa ɖe teƒe gbadza aɖe | megbenyawo me yɔ fũ akpa: da aŋgba la ɖe anyigba gbadza aɖe dzi | 0.76 | trop de fond : placez la feuille sur une surface plane | yes |
| `guard_no_leaf` | je ne vois pas bien la feuille | Nyemate ŋu akpɔ aŋgba la nyuie o | Nyemate ŋu akpɔ aŋgba la nyuie o | 1.00 | Je ne vois pas clairement la feuille | yes |
| `guard_background_too_colourful` | le fond est trop coloré : posez la feuille sur une surface unie | megbenyawo le amadede vovovowo me akpa: da agbalẽa ɖe teƒe gbadza aɖe | megbenyawo le amadede vovovowo me akpa: da aŋgba la ɖe anyigba gbadza aɖe dzi | 0.88 | le fond est trop coloré : placez la feuille sur une surface plane | yes |
| `guard_save_without` | Enregistrer sans diagnostic | Dzra ga ɖo evɔ womakpɔ dɔlélea o | Dzra ga ɖo ne womekpɔ dɔlélea le eŋu o | 0.83 | Économisez de l'argent sans être diagnostiqué | yes |
| `result_high` | Problème probable | Kuxi si anya nɔ anyi | Kuxi si anya nɔ anyi | 1.00 | Problème possible | yes |
| `result_medium` | Possible, mais je ne suis pas sûr | Ate ŋu adzɔ, gake nyemeka ɖe edzi o | Ate ŋu adzɔ, gake nyemeka ɖe edzi o | 1.00 | C'est possible, mais je ne suis pas sûr | yes |
| `result_low` | Je ne peux pas identifier ce problème | Nyemate ŋu ade dzesi kuxi sia o | Nyemate ŋu ade dzesi kuxi sia o | 1.00 | Je n'arrive pas à identifier ce problème | yes |
| `result_low_body` | Je ne suis pas assez sûr pour donner un diagnostic. Montrez cette feuille à un agent de vulgarisation agricole. | Nyemeka ɖe edzi ale gbegbe be mate ŋu ana dɔléle aɖe ƒe dzesi o. Fia agbalẽvi sia na agbledede ƒe kekeɖenudɔdzikpɔla. | Nyemeka ɖe edzi ale gbegbe be mate ŋu agblɔ dɔléle si le ŋunye o. Taflatse tsɔ aŋgba sia fia agbledede ƒe kekeɖenudɔdzikpɔla. | 0.83 | Je ne suis pas sûr de pouvoir poser un diagnostic. Montrez ce formulaire à l'agent de vulgarisation sur le terrain. | yes |
| `result_medium_warn` | Ce n'est pas un diagnostic. Faites confirmer par un agent de vulgarisation avant d'agir. | Menye dɔléle si wokpɔnae wònye o. Xɔ kpeɖodzi tso kekeɖenudɔdzikpɔla gbɔ hafi nàwɔ afɔɖeɖe. | Esia menye dɔléle si wokpɔna o. Na kekeɖenudɔdzikpɔla aɖe naɖo kpe edzi hafi nàwɔ nane. | 0.69 | Ce n'est pas un diagnostic. Obtenez la confirmation de l’administrateur de l’extension avant d’agir. | yes |
| `confidence` | Confiance | Ka ɖe edzi | Kakaɖedzi | 0.74 | Bien sûr | yes |
| `other_possibility` | Autre possibilité | Nu bubu si ate ŋu adzɔ | Nu bubu siwo ate ŋu adzɔ | 0.96 | Une autre possibilité | yes |
| `what_to_do` | Que faire | Nusi woawɔ | Nusi woawɔ | 1.00 | Ce qu'il faut faire | yes |
| `ask_note` | Conseil général à confirmer : | Aɖaŋuɖoɖo gbadza siwo dzi woaɖo kpee: | Aɖaŋuɖoɖo gbadza siwo dzi woaɖo kpee: | 1.00 | Conseils généraux à confirmer : | yes |
| `limits_note` | Testé sur des photos de feuilles d'arabica posées sur fond uni. Je ne connais que 4 problèmes : mineuse, rouille, phoma et cercosporiose. Une feuille « saine » ici ne garantit pas que la plante va bien. | Wodoe kpɔ le arabica aŋgba siwo woda ɖe megbe gbadzaa ƒe fotowo dzi. Kuxi 4 koe menya: aŋgbawo, gbeɖuɖɔ, phoma kple Sigatoka. Agba si “le lãmesẽ” si le afisia meka ɖe edzi be numiemiea le dɔ wɔm nyuie o. | Wodoe kpɔ le Arabica aŋgba siwo wotsɔ mlɔ megbe gbadzaa ƒe fotowo dzi. Kuxi 4 koe menya: aŋgba kuku, gbeɖuɖɔ, phoma kple cercospora. Agba si “le lãmesẽ” si le afisia meka ɖe edzi be numiemiea nyo o. | 0.89 | Testé sur des photographies de feuilles d'arabica placées à plat. Je ne connais que 4 problèmes : les feuilles, la rouille, le phoma et la cercosporiose. Une feuille « saine » ne garantit pas ici que la plante se porte bien. | yes |
| `validate_note` | Conseils généraux, pas encore validés par un agronome. Cet outil aide à décider ; c'est vous et l'agent de vulgarisation qui décidez. | Aɖaŋuɖoɖo si wozãna le mɔ gbadza nu, si dzi agbledela aɖeke meda asi ɖo haɖe o. Dɔwɔnu sia kpena ɖe ŋuwò nètsoa nya me; wò ŋutɔ kple kekeɖenudɔdzikpɔla gbɔe wòtso. | Aɖaŋuɖoɖo si wozãna le mɔ gbadza nu, si dzi agbledela aɖeke meda asi ɖo haɖe o. Dɔwɔnu sia doa alɔ nyametsotso aɖe; wò kple kekeɖenudɔdzikpɔla lae miewɔnɛ. | 0.84 | Conseils généraux, encore adoptés par aucun agriculteur. Cet outil vous aide à décider ; c'est à vous et à l'agent de vulgarisation de décider. | yes |
| `analyzed_in` | Analysé sur ce téléphone en {ms} ms, sans envoyer votre photo. | Wodzro eme le telefon sia dzi le {ms} ms me, evɔ womeɖo wò foto ɖa o. | Wodzro eme le telefon sia dzi le {ms} ms me, evɔ womeɖo wò foto ɖa o. | 1.00 | Testé sur ce téléphone en 987654 ms, sans envoyer votre photo. | yes |
| `obs_empty` | Aucune observation pour l'instant. | Womekpɔe haɖe o. | Womekpɔe haɖe o. | 1.00 | Ils ne l’ont pas encore trouvé. | yes |
| `obs_pending` | En attente d'envoi | Lala be woaɖoe ɖa | Lala be woaɖo ye ɖa | 0.94 | En attendant qu'il soit envoyé | yes |
| `obs_shared` | Partagé | Mamã | Womae | 0.44 | Maternité | yes |
| `obs_no_diag` | Pas de diagnostic (photo à reprendre) | Womekpɔ dɔléle aɖeke le eŋu o (woaɖe fotoa) . | Womekpɔ dɔléle aɖeke le eŋu o (fotoa be woagaɖee ake) | 0.76 | Pas de diagnostic (photo à prendre) . | yes |
| `send_now` | Envoyer | Dᴐ | Dᴐ | 1.00 | ENVOYER | yes |
| `delete` | Supprimer | ƉE ƉA | Ɖe ɖa | 1.00 | DÉBARRASSER | yes |
| `waiting` | {n} observation(s) en attente d'envoi. Elles restent sur ce téléphone jusqu'à ce que vous les partagiez. | {n} ŋkuléleɖenuŋu(wo) le lalam be woaɖoe ɖa. Wonɔa telefon sia dzi vaseɖe esime nàma wo. | {n} ŋkuléleɖenuŋu(wo) le lalam be woaɖoe ɖa. Wonɔa telefon sia dzi vaseɖe esime nàma wo. | 1.00 | 765432 moniteur(s) en attente de soumission. Ils restent sur ce téléphone jusqu'à ce que vous les partagiez. | yes |
| `share_title` | Observation Esaaka Edge | Esaaka Edge ƒe ŋkuléleɖenuŋu | Esaaka Edge ƒe ŋkuléle ɖe nu ŋu | 0.95 | L'observation d'Esaaka Edge | yes |
| `share_text` | Observation du {date} : {label}. Photo jointe. (Analyse automatique sur téléphone, à confirmer.) | {date} ƒe ŋkuléleɖenuŋu: {label}. Fotoa kpe ɖe eŋu. (Automatic analysis le telefon dzi, woaɖo kpe edzi.) | {date} ƒe ŋkuléleɖenuŋu: {label}. Fotoa kpe ɖe eŋu. (Wowɔa numekuku le wo ɖokui si le telefon dzi, woaɖo kpe edzi.) | 0.85 | Bilan du 12/12/2012 : LABELX. La photo est jointe. (Analyse automatique par téléphone, à confirmer.) | yes |
| `share_unavailable` | Partage indisponible sur cet appareil : la photo est téléchargée, envoyez-la par WhatsApp ou SMS. | Mamã mele mɔ̃ sia dzi o: woɖe fotoa, woɖoe ɖa to WhatsApp alo SMS dzi. | Mamã mele mɔ̃ sia dzi o: woɖe fotoa, woɖoe ɖa to WhatsApp alo SMS dzi. | 1.00 | Il n'y a pas de partage sur cet appareil : la photo a été prise, envoyée via WhatsApp ou SMS. | yes |
| `model_info` | Modèle : {name}, {size} Mo, analyse locale | Kpɔɖeŋu: {name}, {size} MB, nutoa me numekuku | Kpɔɖeŋu: {name}, {size} MB, zɔna le teƒea | 0.79 | Exemple : NAMEX, 1 234,5 Mo, analyse locale | yes |
| `ee_banner` | Traductions éwé en cours de validation : texte affiché en français. | Ewe gbegɔmeɖeɖe siwo dzi wole asi kpem ɖo fifia: nuŋɔŋlɔ siwo woɖe fia le Fransegbe me. | Wole asi kpem ɖe alẽgbe me gɔmeɖeɖewo ŋu: nuŋɔŋlɔ si woɖe fia le Fransegbe me. | 0.67 | Supporte actuellement les traductions en éwé : textes présentés en français. | yes |
| `cls_healthy` | feuille saine | aŋgba si le lãmesẽ me | aŋgba si le lãmesẽ me | 1.00 | une feuille saine | yes |
| `cls_miner` | mineuse des feuilles | aŋgbawo tomenukulawo | aŋgbawo tomenukulawo | 1.00 | laisse les mineurs | yes |
| `cls_rust` | rouille orangée | aŋutiɖiɖi ƒe gbeɖuɖɔ | kɔfi aŋgba ƒe gbeɖuɖɔ | 0.63 | déchets oranges | yes |
| `cls_phoma` | taches de Phoma | Phoma ƒe teƒeteƒewo | Phoma aŋgba ƒe ʋuʋudedi | 0.48 | Taches Phoma | yes |
| `cls_cercospora` | tache brune (Cercospora) | teƒe si ƒe amadede nye aŋutiɖiɖi (Cercospora) . | ŋku ƒe ʋuʋudedi si ƒe amadede nye aŋutiɖiɖi (Cercospora) . | 0.86 | tache brune (Cercospora) . | yes |
| `cls_other` | autre problème ou plusieurs problèmes | kuxi bubu alo kuxi geɖe | kuxi bubu, alo kuxi geɖe | 0.98 | un autre problème ou plusieurs problèmes | yes |