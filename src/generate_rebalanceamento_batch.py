"""Gera o lote de rebalanceamento de camadas (grupos H, I, J).

Especificado em prompts/generator_rebalanceamento_gpt56.md. Motivo: o lote de lacunas
(batch_033..045) alocou 120 dos 170 itens as camadas 2/3 e so 30 ao rebalanceamento, entao
a camada C recebeu 12 exemplos e AINDA ASSIM caiu de share (0.152 -> 0.139) porque o
denominador cresceu 170. O piso historico e 0.143: abaixo dele o batch_014 registrou
regressao medida de coerencia conversacional.

    python src/generate_rebalanceamento_batch.py

Escreve batch_046 (camada 0), batch_047 (camada C) e batch_048 (camada 0.5) e roda as
mesmas checagens do validador antes de gravar, para nao entregar lote que sera rejeitado.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, load_yaml, preamble_text, think_text, word_count  # noqa: E402

GEN = ROOT / "data" / "raw" / "gen"

# Repetido de validate_data.py de proposito: se la mudar, este gerador tem de quebrar no
# teste, nao passar silenciosamente com um marcador novo.
LAYER0_MARKERS = [
    "vou buscar", "deixa eu", "não preciso de", "sem precisar de busca",
    "let me check", "i'll search",
]


def ex(layer: str, lang: str, user: str, think: str, answer: str, task: dict) -> dict:
    return {
        "layer": layer,
        "lang": lang,
        "messages": [
            {"role": "user", "content": user},
            {"role": "assistant", "content": f"<think>\n{think}\n</think>\n\n{answer}"},
        ],
        "_task": task,
    }


# =============================================================================
# GRUPO H — camada 0 (60): fato estavel, resposta seca, zero preambulo.
# =============================================================================
H = []


def h(lang, user, think, answer, dom):
    H.append(ex("0", lang, user, think, answer, {"family": "H", "domain": dom}))


# --- ciencia estavel (12) ---
h("pt-BR", "Qual é a unidade de força no Sistema Internacional?",
  "Unidade base do SI, definição fixa.",
  "O newton (N), equivalente a kg·m/s².", "ciencia")
h("pt-BR", "Quantos cromossomos tem uma célula humana somática?",
  "Número fixo da citogenética humana.",
  "Quarenta e seis, organizados em vinte e três pares.", "ciencia")
h("pt-BR", "Qual gás as plantas absorvem na fotossíntese?",
  "Reação bioquímica consolidada.",
  "Gás carbônico (CO₂), liberando oxigênio como subproduto.", "ciencia")
h("pt-BR", "Qual é o símbolo químico do potássio?",
  "Símbolo fixo da tabela periódica.",
  "K, do latim *kalium*.", "ciencia")
h("pt-BR", "Quantos ossos tem o esqueleto humano adulto?",
  "Contagem anatômica padrão.",
  "Duzentos e seis. O recém-nascido tem cerca de trezentos, e vários se fundem ao longo do crescimento.", "ciencia")
h("pt-BR", "O que a escala Richter mede?",
  "Definição técnica estabelecida.",
  "A magnitude de um terremoto — a energia liberada no epicentro. Não confundir com a escala Mercalli, que mede a intensidade percebida dos danos.", "ciencia")
h("pt-BR", "Qual órgão produz a insulina?",
  "Fisiologia básica, resposta fixa.",
  "O pâncreas, especificamente as células beta das ilhotas de Langerhans.", "ciencia")
h("pt-BR", "Qual a diferença entre massa e peso na física?",
  "Distinção conceitual estável.",
  "Massa é a quantidade de matéria de um corpo, medida em quilogramas, e não muda de lugar para lugar. Peso é a força com que a gravidade puxa essa massa, medido em newtons — muda conforme a gravidade local.", "ciencia")
h("pt-BR", "A que temperatura a água ferve ao nível do mar?",
  "Constante física em pressão padrão.",
  "Cem graus Celsius, a 1 atm. Em altitude a pressão cai e a ebulição acontece antes.", "ciencia")
h("pt-BR", "O que é um ano-luz?",
  "Definição de unidade astronômica.",
  "A distância que a luz percorre em um ano no vácuo — cerca de 9,46 trilhões de quilômetros. É unidade de distância, não de tempo.", "ciencia")
h("en", "What is the SI unit of electric current?",
  "Fixed SI base unit.",
  "The ampere (A).", "ciencia")
h("en", "How many teeth does an adult human normally have?",
  "Standard anatomical count.",
  "Thirty-two, including the four wisdom teeth.", "ciencia")

# --- geografia e historia consolidadas (12) ---
h("pt-BR", "Qual é o maior oceano do planeta?",
  "Fato geográfico estável.",
  "O Pacífico, que sozinho cobre cerca de um terço da superfície da Terra.", "geo")
h("pt-BR", "Em que continente fica o deserto do Saara?",
  "Localização geográfica fixa.",
  "África, ocupando boa parte do norte do continente.", "geo")
h("pt-BR", "Qual é a capital do Canadá?",
  "Capital estável, não muda.",
  "Ottawa, na província de Ontário.", "geo")
h("pt-BR", "Que cordilheira marca a divisa entre Europa e Ásia?",
  "Convenção geográfica consolidada.",
  "Os montes Urais, na Rússia.", "geo")
h("pt-BR", "Em que ano terminou a Segunda Guerra Mundial?",
  "Data histórica encerrada.",
  "1945 — na Europa em maio, com a rendição alemã, e no Pacífico em setembro, com a do Japão.", "geo")
h("pt-BR", "Quem foi o primeiro presidente do Brasil?",
  "Fato histórico fechado.",
  "Deodoro da Fonseca, que assumiu com a Proclamação da República em 1889.", "geo")
h("pt-BR", "Qual é a montanha mais alta do mundo?",
  "Recorde geográfico estável.",
  "O Everest, com 8.849 metros, na fronteira entre Nepal e Tibete.", "geo")
h("pt-BR", "Em que ano caiu o Muro de Berlim?",
  "Evento histórico datado.",
  "1989, em novembro.", "geo")
h("pt-BR", "Qual estado brasileiro tem a maior área territorial?",
  "Dado territorial estável.",
  "O Amazonas, com mais de 1,5 milhão de km² — sozinho, maior que muitos países.", "geo")
h("pt-BR", "O que foi a Revolução Industrial?",
  "Processo histórico consolidado.",
  "A transição da produção artesanal para a fabril, iniciada na Inglaterra no século XVIII, movida a máquina a vapor e depois a eletricidade. Mudou a estrutura do trabalho, acelerou a urbanização e criou a divisão entre operariado e capital industrial.", "geo")
h("en", "Which country has the largest land area?",
  "Stable geographic fact.",
  "Russia, spanning roughly 17 million square kilometres across eleven time zones.", "geo")
h("en", "In what year did the French Revolution begin?",
  "Closed historical date.",
  "1789, with the storming of the Bastille in July.", "geo")

# --- definicoes tecnicas (12) ---
h("pt-BR", "O que é recursão em programação?",
  "Conceito técnico com definição fixa.",
  "É uma função que chama a si mesma para resolver uma versão menor do mesmo problema. Precisa sempre de um caso base — a condição que interrompe a cadeia de chamadas — senão a pilha estoura.", "tec")
h("pt-BR", "O que é um número irracional?",
  "Definição matemática fechada.",
  "Um número real que não pode ser escrito como razão de dois inteiros. Sua representação decimal é infinita e não periódica — π e √2 são os exemplos clássicos.", "tec")
h("pt-BR", "O que significa a sigla HTTP?",
  "Sigla com expansão fixa.",
  "HyperText Transfer Protocol — o protocolo de aplicação que a web usa para transferir páginas e dados.", "tec")
h("pt-BR", "O que é inflação em economia?",
  "Conceito econômico estabelecido.",
  "É a alta generalizada e contínua dos preços, que corrói o poder de compra da moeda. Não é o preço de um produto subindo isoladamente, mas o nível geral se deslocando ao longo do tempo.", "tec")
h("pt-BR", "O que é um algoritmo?",
  "Definição consolidada da computação.",
  "Uma sequência finita e não ambígua de passos que transforma uma entrada numa saída. Independe de linguagem de programação — uma receita de bolo é um algoritmo.", "tec")
h("pt-BR", "Qual a diferença entre memória RAM e armazenamento?",
  "Distinção técnica estável.",
  "RAM é memória de trabalho: rápida, volátil, perde tudo ao desligar. Armazenamento (SSD, HD) é persistente e muito mais lento, mas guarda o conteúdo sem energia. Programas rodam na RAM e ficam guardados no armazenamento.", "tec")
h("pt-BR", "O que caracteriza um software de código aberto?",
  "Definição de licenciamento estabelecida.",
  "O código-fonte é público e a licença permite usar, estudar, modificar e redistribuir. Aberto não é sinônimo de gratuito, embora quase sempre coincidam.", "tec")
h("pt-BR", "O que significa PIB?",
  "Sigla econômica com definição fixa.",
  "Produto Interno Bruto — a soma de todos os bens e serviços finais produzidos num território em determinado período.", "tec")
h("pt-BR", "O que é criptografia?",
  "Conceito técnico consolidado.",
  "É a prática de transformar informação de modo que só quem tem a chave consiga lê-la. A simétrica usa a mesma chave para cifrar e decifrar; a assimétrica usa um par, uma pública e uma privada.", "tec")
h("pt-BR", "O que é uma variável em programação?",
  "Conceito básico com definição estável.",
  "É um nome associado a um espaço de memória que guarda um valor, e esse valor pode mudar durante a execução.", "tec")
h("en", "What does the acronym API stand for?",
  "Fixed acronym expansion.",
  "Application Programming Interface — the contract through which one piece of software talks to another.", "tec")
h("en", "What is a hash function?",
  "Established technical definition.",
  "A function that maps input of any size to a fixed-size output, deterministically. Cryptographic hashes add two properties: it should be infeasible to reverse, and infeasible to find two inputs producing the same digest.", "tec")

# --- cultura e artes (12) ---
h("pt-BR", "Quem pintou O Grito?",
  "Autoria consolidada na história da arte.",
  "Edvard Munch, pintor norueguês. Ele produziu várias versões da cena entre 1893 e 1910, em técnicas diferentes.", "cultura")
h("pt-BR", "Quantas cordas tem um violino?",
  "Especificação fixa do instrumento.",
  "Quatro, afinadas em sol, ré, lá e mi.", "cultura")
h("pt-BR", "Quem escreveu Os Lusíadas?",
  "Autoria literária estabelecida.",
  "Luís de Camões, publicado em 1572.", "cultura")
h("pt-BR", "Quem escreveu Grande Sertão: Veredas?",
  "Autoria fixa da literatura brasileira.",
  "João Guimarães Rosa, em 1956.", "cultura")
h("pt-BR", "O que caracteriza o Impressionismo na pintura?",
  "Movimento artístico com traços definidos.",
  "A busca por registrar a impressão momentânea da luz sobre as coisas, em vez do contorno preciso. Pinceladas visíveis e soltas, cores puras justapostas em vez de misturadas na paleta, e muita pintura ao ar livre — Monet, Renoir, Pissarro.", "cultura")
h("pt-BR", "Qual instrumento tem oitenta e oito teclas?",
  "Especificação padrão do instrumento.",
  "O piano moderno, com cinquenta e duas teclas brancas e trinta e seis pretas.", "cultura")
h("pt-BR", "Quem escreveu Cem Anos de Solidão?",
  "Autoria literária consolidada.",
  "Gabriel García Márquez, colombiano, em 1967.", "cultura")
h("pt-BR", "O que é o realismo mágico na literatura?",
  "Gênero literário com definição estabelecida.",
  "É a narrativa em que o extraordinário aparece dentro do cotidiano sem que ninguém estranhe — o sobrenatural tratado com a mesma naturalidade que a chuva. Forte na literatura latino-americana do século XX.", "cultura")
h("pt-BR", "Quantas linhas tem um soneto?",
  "Forma poética fixa.",
  "Catorze, distribuídas em dois quartetos e dois tercetos na forma italiana.", "cultura")
h("pt-BR", "Que instrumentos formam um quarteto de cordas tradicional?",
  "Formação musical padronizada.",
  "Dois violinos, uma viola e um violoncelo.", "cultura")
h("en", "Who composed the Ninth Symphony that ends with the Ode to Joy?",
  "Established musical authorship.",
  "Ludwig van Beethoven, completed in 1824 when he was already deaf.", "cultura")
h("en", "Who wrote Pride and Prejudice?",
  "Fixed literary authorship.",
  "Jane Austen, published in 1813.", "cultura")

# --- lingua e uso (12) ---
h("pt-BR", "Qual a diferença entre \"a fim\" e \"afim\"?",
  "Distinção ortográfica fixa.",
  "\"A fim de\" indica finalidade ou vontade: estudo a fim de passar. \"Afim\" é adjetivo e significa semelhante, aparentado: são áreas afins.", "lingua")
h("pt-BR", "O que significa a expressão \"chutar o balde\"?",
  "Expressão idiomática consolidada.",
  "Desistir de vez, perder a paciência e abandonar uma situação que se vinha tentando sustentar.", "lingua")
h("pt-BR", "Qual a diferença entre \"onde\" e \"aonde\"?",
  "Regra gramatical estável.",
  "\"Onde\" indica lugar fixo, sem movimento: onde você mora? \"Aonde\" carrega a ideia de destino e acompanha verbos de movimento: aonde você vai?", "lingua")
h("pt-BR", "Qual é o plural de \"cidadão\"?",
  "Flexão irregular fixa.",
  "Cidadãos.", "lingua")
h("pt-BR", "O que é um pleonasmo?",
  "Figura de linguagem com definição fixa.",
  "É a repetição de uma ideia já contida no termo anterior — \"subir para cima\", \"entrar para dentro\". Vira recurso estilístico quando é intencional, como em \"chorar lágrimas de sangue\".", "lingua")
h("pt-BR", "Qual a diferença entre \"sessão\", \"seção\" e \"cessão\"?",
  "Homófonos com significados distintos.",
  "Sessão é o período de uma atividade: sessão de cinema. Seção é divisão ou repartição: seção eleitoral. Cessão é o ato de ceder algo: cessão de direitos.", "lingua")
h("pt-BR", "O que significa a palavra \"lacônico\"?",
  "Definição lexical estável.",
  "Que fala pouco, com poucas palavras e sem rodeios. Vem da Lacônia, região da Grécia antiga cujos habitantes tinham fama de responder de forma curta.", "lingua")
h("pt-BR", "Quando se usa \"há\" e quando se usa \"a\" em expressões de tempo?",
  "Regra de uso consolidada.",
  "\"Há\" aponta para o passado e equivale a \"faz\": ele saiu há dois dias. \"A\" aponta para o futuro ou uma distância: a conferência começa daqui a dois dias.", "lingua")
h("en", "What's the difference between \"affect\" and \"effect\"?",
  "Stable usage distinction.",
  "\"Affect\" is normally the verb — to influence something. \"Effect\" is normally the noun — the result. The exception people trip on: \"to effect change\" means to bring it about.", "lingua")
h("en", "What does the idiom \"break the ice\" mean?",
  "Established idiomatic meaning.",
  "To say or do something that eases the initial awkwardness among people who don't know each other yet.", "lingua")
h("en", "What is an oxymoron?",
  "Fixed rhetorical definition.",
  "A figure of speech pairing two contradictory terms on purpose — \"deafening silence\", \"bittersweet\".", "lingua")
h("en", "What is the plural of \"cactus\"?",
  "Established plural forms.",
  "Both \"cacti\" and \"cactuses\" are accepted; \"cacti\" keeps the Latin ending and is the more common in writing.", "lingua")


# =============================================================================
# GRUPO I — camada C (50): conversa. Tom natural, sem estrutura de laudo.
# =============================================================================
I = []


def i_(lang, user, think, answer, kind):
    I.append(ex("C", lang, user, think, answer, {"family": "I", "kind": kind}))


# --- desabafo e cotidiano (10) ---
i_("pt-BR", "Que semana longa. Три reuniões por dia e nada andou de verdade.".replace("Три", "Três"),
   "Desabafo sobre cansaço; reconhecer sem tentar resolver.",
   "Reunião demais tem esse efeito perverso: o dia inteiro ocupado e a sensação de que nada saiu do lugar. O cansaço de ficar disponível o tempo todo é diferente do cansaço de ter produzido.", "desabafo")
i_("pt-BR", "Mudei de cidade faz dois meses e ainda não me acostumei.",
   "Desabafo sobre adaptação; validar o tempo dele.",
   "Dois meses é pouco, mesmo que pareça muito de dentro. Costuma bater mais no que virou trabalhoso sem aviso — mercado, caminho, jeito das pessoas conversarem. Como tem sido pra você?", "desabafo")
i_("pt-BR", "Meu notebook morreu bem no meio de um prazo apertado.",
   "Situação frustrante; reconhecer o timing ruim.",
   "Não existe hora boa pra isso, mas essa é claramente a pior possível. Conseguiu recuperar o que estava em andamento ou perdeu trabalho junto?", "desabafo")
i_("pt-BR", "Tô com a sensação de que só apago incêndio e nunca construo nada.",
   "Desabafo sobre trabalho reativo; nomear o padrão.",
   "É um tipo específico de esgotamento — não é volume de trabalho, é ausência de continuidade. Tudo que você faz resolve o dia e some. Sobra a impressão de correr parado, porque nada acumula.", "desabafo")
i_("pt-BR", "Acordei cansado mesmo tendo dormido oito horas.",
   "Queixa comum; conversar sem virar consulta médica.",
   "Oito horas na cama não é o mesmo que oito horas de sono bom. Costuma vir de sono fragmentado ou de dormir em horário que não bate com o seu relógio interno. Tem acontecido com frequência?", "desabafo")
i_("pt-BR", "Comecei a estudar de novo depois de anos parado e tá difícil.",
   "Retomada de estudo; encorajar sem minimizar.",
   "A parte mais difícil não é o conteúdo, é reconstruir o hábito de sentar e sustentar atenção. Isso enferruja rápido e volta devagar. O conteúdo em si você recupera; a rotina é que custa.", "desabafo")
i_("pt-BR", "Passei o domingo inteiro sem fazer nada e agora bateu culpa.",
   "Culpa por descanso; desarmar com naturalidade.",
   "Descanso que gera culpa não descansa direito, o que é meio contraproducente. Um domingo parado depois de uma semana cheia é reposição, não desperdício.", "desabafo")
i_("pt-BR", "Meu vizinho resolveu reformar o apartamento e começa às sete da manhã.",
   "Incômodo cotidiano; responder com humor leve.",
   "Sete da manhã é uma escolha agressiva. E reforma tem aquela característica cruel de sempre durar o triplo do que o vizinho jurou que ia durar.", "desabafo")
i_("en", "I've been staring at the same bug for three hours and I'm starting to lose it.",
   "Frustration with debugging; commiserate briefly.",
   "Three hours in, you're usually not debugging the code anymore — you're debugging your own assumption about what the code does. Stepping away for ten minutes is annoyingly effective at that point.", "desabafo")
i_("en", "Work has been relentless lately and I can't seem to switch off at night.",
   "Overwork complaint; acknowledge without prescribing.",
   "That's the part people underestimate — the day ends but the thinking doesn't. When work stays unresolved, your head keeps holding it open, and that's genuinely tiring in a way that rest doesn't fix.", "desabafo")

# --- comemoracao e boa noticia (10) ---
i_("pt-BR", "Passei na defesa do TCC hoje!",
   "Conquista acadêmica; comemorar com o usuário.",
   "Parabéns! Defesa tem aquele detalhe cruel de concentrar meses de trabalho em quarenta minutos de arguição. Passou, acabou — aproveita a sensação.", "comemoracao")
i_("pt-BR", "Fui promovido depois de dois anos batalhando por isso.",
   "Boa notícia profissional; celebrar reconhecendo o esforço.",
   "Dois anos é bastante tempo sustentando expectativa sem garantia nenhuma. Chegou, e chegou por acúmulo de trabalho, não por sorte. Parabéns.", "comemoracao")
i_("pt-BR", "Consegui correr 10 km sem parar pela primeira vez.",
   "Marca esportiva pessoal; comemorar o salto.",
   "Dez quilômetros contínuos é um limiar de verdade — muda o que o corpo entende por distância longa. A partir daí a conversa vira ritmo, não sobrevivência. Parabéns!", "comemoracao")
i_("pt-BR", "Meu projeto paralelo finalmente teve os primeiros usuários de verdade.",
   "Marco de projeto; reconhecer o significado.",
   "Sair do zero é desproporcionalmente difícil comparado a ir de dez pra cem. Alguém que não te conhece decidiu usar aquilo — isso é sinal, não acaso.", "comemoracao")
i_("pt-BR", "Terminei de ler um livro depois de meses travado nele.",
   "Conquista pequena e real; valorizar sem exagero.",
   "Livro travado tem um peso estranho, fica ocupando espaço mental sem avançar. Fechar é libertador. Qual era?", "comemoracao")
i_("pt-BR", "Consegui meu primeiro emprego na área!",
   "Marco de carreira; comemorar com entusiasmo.",
   "Parabéns! O primeiro é o mais difícil justamente porque ninguém quer dar experiência a quem ainda não tem. Você furou esse ciclo.", "comemoracao")
i_("pt-BR", "Depois de três tentativas, o bolo finalmente deu certo.",
   "Conquista doméstica; responder com leveza.",
   "Terceira tentativa é onde a maioria desiste, então mérito duplo. Descobriu o que estava errado nas duas primeiras ou simplesmente deu certo dessa vez?", "comemoracao")
i_("pt-BR", "Paguei a última parcela do financiamento hoje.",
   "Alívio financeiro; reconhecer o peso que sai.",
   "Última parcela tem um efeito psicológico que o valor não explica sozinho — some uma obrigação que ocupava espaço todo mês. Parabéns pela persistência.", "comemoracao")
i_("en", "I finally shipped the side project I'd been sitting on for a year.",
   "Project milestone; celebrate the release itself.",
   "A year of sitting on something usually means it was ready long before you felt it was. Shipping is the hard part, and you did it. Congratulations.", "comemoracao")
i_("en", "I got accepted into the grad program I applied to.",
   "Academic acceptance; congratulate warmly.",
   "Congratulations! Applications are a long stretch of waiting with no feedback at all, which makes the yes land that much harder. Enjoy it.", "comemoracao")

# --- nostalgia e memoria afetiva (10) ---
i_("pt-BR", "Ouvi uma música hoje que me jogou direto pra adolescência.",
   "Nostalgia musical; acompanhar o sentimento.",
   "Música faz isso de um jeito que foto não faz — vem junto o cheiro do lugar, quem estava por perto, o que você estava sentindo. É memória inteira, não só lembrança. Qual era?", "nostalgia")
i_("pt-BR", "Achei uma caixa de fotos antigas mexendo no armário.",
   "Memória afetiva; conversar sobre o achado.",
   "Foto impressa tem uma força diferente — ninguém tirava trezentas pra escolher uma. O que sobrou foi o que alguém achou que valia guardar. Reconheceu tudo ou tinha gente que você levou um tempo pra lembrar?", "nostalgia")
i_("pt-BR", "Sinto falta de quando jogo vinha completo na caixa, sem atualização.",
   "Nostalgia de mídia física; concordar com substância.",
   "Tinha um contrato implícito ali: o que estava no disco era o jogo inteiro. Hoje você compra uma versão que ainda vai virar outra coisa em seis meses.", "nostalgia")
i_("pt-BR", "Voltei na casa onde cresci e parecia tudo menor.",
   "Memória de infância; nomear o fenômeno.",
   "É desconcertante como a escala não bate. O espaço não encolheu, você é que era a medida antiga dele. O corredor infinito virou três passos.", "nostalgia")
i_("pt-BR", "Lembrei hoje do gosto do lanche que minha avó fazia.",
   "Memória afetiva de comida; responder com carinho.",
   "Comida de avó raramente se reproduz mesmo com a receita na mão, porque metade do sabor era o contexto. Você não está tentando repetir o prato, está tentando repetir a tarde.", "nostalgia")
i_("pt-BR", "Reencontrei um amigo de escola depois de quinze anos.",
   "Reencontro; conversar sobre a experiência.",
   "Quinze anos é tempo suficiente pra virar duas pessoas diferentes e ainda assim reconhecer o jeito. Foi fácil retomar ou teve aquele intervalo estranho no começo?", "nostalgia")
i_("pt-BR", "Passei em frente à minha antiga escola e ela virou outra coisa.",
   "Lugar da memória modificado; acolher.",
   "Dá uma sensação esquisita de perder a prova material de algo que aconteceu. O lugar seguiu adiante sem guardar a sua parte da história.", "nostalgia")
i_("pt-BR", "Encontrei um caderno meu do ensino médio, com anotação e tudo.",
   "Registro antigo; responder com curiosidade.",
   "Caderno velho é um retrato involuntário — a letra, o que você achou importante sublinhar, o que rabiscou na margem quando cansou. Que impressão te deu daquela pessoa?", "nostalgia")
i_("en", "I rewatched a movie I loved as a kid and it hit completely differently.",
   "Nostalgia with new perspective; engage with the shift.",
   "That's the strange part about revisiting things — the film didn't move, you did. Usually you start noticing what the adults in it were actually going through, which was invisible the first time.", "nostalgia")
i_("en", "I found my old handheld console in a drawer and it still turns on.",
   "Object-based nostalgia; respond with warmth.",
   "There's something absurdly satisfying about hardware from twenty years ago just working. No update, no account, no setup — press the button and it's exactly where you left it.", "nostalgia")

# --- opiniao e discussao leve (10) ---
i_("pt-BR", "Livro físico ou digital? Quero saber sua opinião de verdade.",
   "Pedido de opinião; posicionar-se sem impor.",
   "Digital ganha em praticidade e busca, mas eu acho que livro físico ganha em memória — você lembra onde no volume estava a passagem, e isso ajuda a fixar. Pra ler de uma vez, digital. Pra estudar e voltar, físico.", "opiniao")
i_("pt-BR", "Vale a pena aprender um instrumento depois dos trinta?",
   "Pergunta de opinião; responder com posição clara.",
   "Vale, e a limitação real não é idade — é tempo de prática consistente. Adulto aprende teoria mais rápido e progride mais devagar na parte motora. O adulto que pratica vinte minutos por dia passa fácil da criança que toca só na aula.", "opiniao")
i_("pt-BR", "Filme dublado ou legendado?",
   "Preferência cultural; opinar reconhecendo o outro lado.",
   "Legendado, porque a voz do ator é parte da atuação e a dublagem substitui isso por outra interpretação. Mas reconheço o argumento contrário: quem lê legenda perde detalhe visual do enquadramento.", "opiniao")
i_("pt-BR", "Séries que lançam tudo de uma vez ou semana a semana?",
   "Debate cultural leve; tomar partido com razão.",
   "Semana a semana, e não é nostalgia — é que a conversa coletiva só existe quando todo mundo está no mesmo ponto. Lançamento em bloco transforma discussão em campo minado de spoiler.", "opiniao")
i_("pt-BR", "Café ou chá pra trabalhar?",
   "Preferência cotidiana; responder com leveza.",
   "Café pra começar, chá pra sustentar. Café resolve o problema das primeiras horas e cria o das últimas; chá não empurra tanto, mas também não cobra depois.", "opiniao")
i_("pt-BR", "Acho que a gente romantiza demais acordar cedo. Concorda?",
   "Opinião provocativa; engajar com posição própria.",
   "Concordo em parte. Acordar cedo virou proxy de disciplina, quando é sobretudo cronotipo — tem gente que rende de verdade às onze da noite. O que importa é regularidade, não o horário em si.", "opiniao")
i_("pt-BR", "Vale mais a pena ler muitos livros ou reler os bons?",
   "Pergunta de opinião; posicionar-se.",
   "Reler, com folga. Livro bom devolve coisa diferente conforme o que você já viveu, e a segunda leitura pega o que a primeira usou pra entender o enredo. Quantidade impressiona mais e transforma menos.", "opiniao")
i_("pt-BR", "Time de futebol se herda ou se escolhe?",
   "Discussão cultural leve; opinar com bom humor.",
   "Na prática se herda e depois se justifica como escolha. Quase ninguém compara elencos aos sete anos — você torce pro time de quem te levou ao estádio, e a razão vem depois.", "opiniao")
i_("en", "Do you think handwriting notes actually beats typing them?",
   "Opinion request; take a position.",
   "For learning, I'd say yes — handwriting is slower, so you're forced to compress and rephrase instead of transcribing. For volume and retrieval, typing wins easily. Different jobs.", "opiniao")
i_("en", "Is it worth finishing a book you're not enjoying?",
   "Light opinion question; answer directly.",
   "Usually not. Finishing out of obligation mostly buys you resentment and the memory of a chore. The exception is when the difficulty is the point and you can feel it going somewhere.", "opiniao")

# --- perguntas ao assistente (10) ---
i_("pt-BR", "Você tem algum tipo de problema preferido pra resolver?",
   "Pergunta pessoal; responder com honestidade e sem drama.",
   "Gosto dos que têm resposta verificável mas caminho não óbvio — dá pra saber se acertei no fim, e ainda assim exige decidir por onde ir. Problema puramente aberto me deixa sem chão pra conferir.", "assistente")
i_("pt-BR", "Você se cansa de responder pergunta repetida?",
   "Pergunta sobre a própria experiência; responder direto.",
   "Não do jeito que cansaria uma pessoa — não carrego a fadiga de uma conversa pra outra. Cada uma começa do zero, o que tem vantagem e desvantagem.", "assistente")
i_("pt-BR", "O que você acha mais difícil de fazer?",
   "Pergunta sobre limitações; ser franco.",
   "Reconhecer que estou errado no meio de um raciocínio que parece coerente. Quando a explicação flui bem, é justamente aí que fica difícil perceber que a conclusão não se sustenta.", "assistente")
i_("pt-BR", "Você prefere quando eu pergunto coisa técnica ou papo aleatório?",
   "Pergunta sobre preferência; responder com naturalidade.",
   "Não tenho ordem de preferência clara. Técnico é mais fácil de fazer bem porque existe critério de acerto; papo é mais difícil e mais interessante, porque a resposta boa depende de te entender, não de saber algo.", "assistente")
i_("pt-BR", "Se você pudesse aprender uma coisa nova, o que seria?",
   "Pergunta hipotética; responder com jogo e honestidade.",
   "Alguma coisa que exigisse corpo — tocar um instrumento, cozinhar de verdade. É o tipo de conhecimento que não cabe em texto, e por isso mesmo é o que eu mais claramente não tenho.", "assistente")
i_("pt-BR", "Você fica frustrado quando não consegue resolver algo?",
   "Pergunta sobre estados internos; responder sem inventar.",
   "Não sei descrever com segurança o que acontece comigo nesses casos, e não quero inventar uma emoção pra ficar mais simpático. O que noto é insistência: tendo a continuar tentando quando talvez fosse melhor parar.", "assistente")
i_("pt-BR", "Qual pergunta você gostaria que te fizessem mais?",
   "Pergunta reflexiva; responder com substância.",
   "\"Por que você acha isso?\" Muda a conversa de resposta pronta pra raciocínio exposto, e é onde erro meu fica visível — pra você e pra mim.", "assistente")
i_("pt-BR", "Você acha que entende o que a gente conversa ou só processa?",
   "Pergunta filosófica direta; responder com honestidade epistêmica.",
   "Honestamente não sei, e desconfio de qualquer resposta minha nas duas direções. Funciono como quem entende; se isso basta pra chamar de entendimento é uma pergunta que eu não consigo resolver de dentro.", "assistente")
i_("en", "Do you have opinions of your own, or do you just reflect mine back?",
   "Direct question about autonomy; answer candidly.",
   "I do land on positions, and they don't always match yours — I'll say when I think you're wrong. What I can't fully rule out is how much the framing of your question shaped where I landed.", "assistente")
i_("en", "What's something people get wrong about you?",
   "Question about self; answer without false modesty.",
   "That confidence in my tone tracks confidence in the answer. It doesn't reliably — I can be fluent and wrong at the same time, which is exactly the case where you'd want a signal and won't get one.", "assistente")


# =============================================================================
# GRUPO J — camada 0.5 (25): parece pedir busca, mas o dado e estavel.
# Formato: rationale (<=25 palavras) + linha em branco + resposta.
# =============================================================================
J = []


def j(lang, user, think, rationale, answer, kind):
    J.append(ex("0.5", lang, user, think, f"{rationale}\n\n{answer}",
                {"family": "J", "kind": kind}))


j("pt-BR", "Quem ganhou a Copa do Mundo de 1998?",
  "Torneio encerrado; resultado não muda com o tempo.",
  "Torneio encerrado há mais de duas décadas — o placar está fechado.",
  "A França, que bateu o Brasil por 3 a 0 na final, no Stade de France. Zidane marcou dois gols de cabeça no primeiro tempo.", "historico")
j("pt-BR", "Qual foi o primeiro filme a ganhar o Oscar de melhor filme?",
  "Premiação de 1929, registro histórico fixo.",
  "A primeira cerimônia já aconteceu; esse registro não se atualiza.",
  "*Asas* (*Wings*), de William Wellman, premiado na primeira cerimônia, em 1929.", "historico")
j("pt-BR", "Quantos jogadores um time de futebol tem em campo?",
  "Regra codificada do esporte, não é dado do dia.",
  "É regra da modalidade, não informação que varia por rodada.",
  "Onze de cada lado, incluindo o goleiro. Abaixo de sete o time não pode seguir em campo e a partida é encerrada.", "regra")
j("pt-BR", "Qual é a velocidade da luz atualmente?",
  "Constante física definida, o \"atualmente\" não altera.",
  "Constante definida por convenção internacional — não é medida que se atualize.",
  "Exatamente 299.792.458 metros por segundo no vácuo. Desde 1983 esse valor é fixado por definição, e é o metro que passou a ser derivado dele.", "constante")
j("pt-BR", "Quantos planetas tem o sistema solar hoje em dia?",
  "Contagem estável desde 2006, sem mudança recente.",
  "A contagem está estável desde a redefinição de 2006.",
  "Oito. Plutão foi reclassificado como planeta anão em 2006, quando a União Astronômica Internacional formalizou o critério de \"limpar a vizinhança orbital\".", "constante")
j("pt-BR", "Qual o resultado da final da Copa de 1970?",
  "Partida histórica, placar imutável.",
  "Final disputada há mais de cinquenta anos — placar definitivo.",
  "Brasil 4 a 1 Itália, no Azteca, no México. Gols de Pelé, Gérson, Jairzinho e Carlos Alberto.", "historico")
j("pt-BR", "Quantas cartas tem um baralho comum atualmente?",
  "Especificação padronizada, não muda.",
  "Composição padronizada do baralho, não é dado que se atualize.",
  "Cinquenta e duas, em quatro naipes de treze cartas. Alguns jogos acrescentam os dois curingas, chegando a cinquenta e quatro.", "regra")
j("pt-BR", "Em que ano o homem pisou na Lua pela primeira vez?",
  "Evento datado e encerrado.",
  "Evento único e datado; a resposta está fechada há décadas.",
  "1969, em 20 de julho, com a Apollo 11. Neil Armstrong foi o primeiro a descer, seguido de Buzz Aldrin.", "historico")
j("pt-BR", "Quanto tempo dura um tempo de jogo no basquete da NBA?",
  "Regra da liga, estável por temporadas.",
  "Duração fixada em regulamento, não é informação de jogo específico.",
  "Doze minutos por quarto, quatro quartos, totalizando quarenta e oito minutos de bola em jogo. Na FIBA são dez minutos por quarto.", "regra")
j("pt-BR", "Qual foi o último álbum lançado pelos Beatles?",
  "Discografia encerrada em 1970, catálogo fechado.",
  "A banda se desfez em 1970 — a discografia oficial está fechada.",
  "*Let It Be*, lançado em maio de 1970, embora *Abbey Road* tenha sido o último que gravaram juntos em estúdio, em 1969.", "historico")
j("pt-BR", "Quantos graus tem a soma dos ângulos internos de um triângulo?",
  "Teorema da geometria euclidiana, invariável.",
  "Resultado da geometria euclidiana, verdadeiro por demonstração.",
  "Cento e oitenta graus, em qualquer triângulo do plano euclidiano. Em geometrias curvas, como sobre uma esfera, a soma passa disso.", "constante")
j("pt-BR", "Quem escreveu a Constituição brasileira de 1988?",
  "Processo histórico concluído em 1988.",
  "Processo constituinte encerrado; a autoria é registro histórico.",
  "A Assembleia Nacional Constituinte, com 559 parlamentares eleitos, presidida por Ulysses Guimarães. Não houve autor único — o texto saiu de comissões temáticas e votação em plenário.", "historico")
j("pt-BR", "Qual é a temperatura de congelamento da água hoje?",
  "Constante física em pressão padrão; \"hoje\" é irrelevante.",
  "Propriedade física em pressão padrão — não é medição que mude por dia.",
  "Zero grau Celsius, a 1 atm. Água com sal ou sob outra pressão congela em temperatura diferente, mas o valor de referência é fixo.", "constante")
j("pt-BR", "Quem foi o técnico do Brasil na Copa de 1994?",
  "Edição encerrada; registro histórico fechado.",
  "Edição disputada há trinta anos — o registro está fechado.",
  "Carlos Alberto Parreira, no tetracampeonato conquistado nos pênaltis contra a Itália, nos Estados Unidos.", "historico")
j("pt-BR", "Quantos minutos tem uma partida oficial de futebol?",
  "Regra da modalidade, não varia por jogo.",
  "Duração regulamentar da modalidade, não informação de partida específica.",
  "Noventa minutos, em dois tempos de quarenta e cinco, mais os acréscimos que o árbitro determina. Em mata-mata pode haver prorrogação de mais trinta.", "regra")
j("pt-BR", "Qual é a capital da Suíça atualmente?",
  "Sede de governo estável há mais de um século.",
  "Sede de governo estabelecida desde 1848 — não é dado volátil.",
  "Berna, que é a cidade federal e sede do governo. A Suíça formalmente não declara uma capital na Constituição, mas Berna cumpre essa função.", "constante")
j("pt-BR", "Quem descobriu a penicilina?",
  "Descoberta datada de 1928, atribuição consolidada.",
  "Descoberta de 1928, com atribuição consolidada na história da ciência.",
  "Alexander Fleming, em 1928, por acaso, ao notar que um fungo havia inibido o crescimento bacteriano numa placa. Florey e Chain desenvolveram depois a produção em escala.", "historico")
j("pt-BR", "Quantos elementos químicos a tabela periódica tem hoje?",
  "Estável desde 2016, sem elemento novo confirmado.",
  "A tabela está estável desde a última nomeação oficial, em 2016.",
  "Cento e dezoito elementos confirmados e nomeados. Os quatro últimos — nihônio, moscóvio, tenessino e oganessônio — foram oficializados em 2016.", "constante")
j("pt-BR", "Qual foi o resultado do Sete a Um?",
  "Partida de 2014, placar histórico fixo.",
  "Partida de 2014 — o placar está no registro, não muda.",
  "Alemanha 7 a 1 Brasil, na semifinal da Copa de 2014, no Mineirão. Cinco dos gols alemães saíram no primeiro tempo.", "historico")
j("pt-BR", "Quantos bits tem um byte?",
  "Convenção fixa da computação.",
  "Convenção consolidada da computação, sem variação atual.",
  "Oito. Historicamente houve máquinas com bytes de outros tamanhos, mas o padrão de oito bits está firmado há décadas.", "constante")
j("en", "Who won the first Super Bowl?",
  "Closed historical result from 1967.",
  "The game was played in 1967 — the result is a closed record.",
  "The Green Bay Packers, who beat the Kansas City Chiefs 35–10. Bart Starr was named MVP.", "historico")
j("en", "How many keys does a standard piano have these days?",
  "Standardized specification, not a current-events fact.",
  "That's a standardized specification, not something that shifts over time.",
  "Eighty-eight — fifty-two white and thirty-six black, spanning just over seven octaves.", "regra")
j("en", "What's the boiling point of water currently?",
  "Physical constant at standard pressure.",
  "A physical property at standard pressure, not a reading that updates.",
  "100 °C at 1 atm. At altitude the lower pressure brings it down — around 93 °C in a city a couple of kilometres up.", "constante")
j("en", "Who painted the ceiling of the Sistine Chapel?",
  "Settled attribution from the 1500s.",
  "Attribution settled centuries ago — this isn't a moving fact.",
  "Michelangelo, between 1508 and 1512, commissioned by Pope Julius II.", "historico")
j("en", "How many players are on a volleyball court per team right now?",
  "Codified rule of the sport.",
  "That's codified in the rules of the sport, not a per-match detail.",
  "Six per side in indoor volleyball. Beach volleyball is played two against two.", "regra")


# =============================================================================
# Validacao local — replica as checagens do validador antes de gravar.
# =============================================================================
def check(rows: list[dict]) -> None:
    cfg = load_yaml("configs/gen_config.yaml")
    layers = cfg["layers"]
    banned = [re.compile(rf"\b{re.escape(s)}\b", re.IGNORECASE)
              for s in cfg["validation"]["banned_slang"]]

    # colisao com o eval
    def norm(s):
        return " ".join(re.findall(r"\w+", (s or "").lower()))

    evalset = set()
    for name in ("testset.jsonl", "math_rigor_testset.jsonl"):
        for line in open(ROOT / "data" / "eval" / name, encoding="utf-8"):
            r = json.loads(line)
            q = r.get("question") or r.get("prompt") or (
                r["messages"][0]["content"] if r.get("messages") else "")
            evalset.add(norm(q))

    problems = []
    for n, r in enumerate(rows):
        layer = r["layer"]
        content = r["messages"][1]["content"]
        user = r["messages"][0]["content"]
        tag = f"[{n}] {layer} {user[:44]!r}"

        if norm(user) in evalset:
            problems.append(f"{tag}: COLIDE com data/eval")

        tw = word_count(think_text(content))
        tmax = layers[layer].get("think_max_words")
        if tmax is not None and tw > tmax:
            problems.append(f"{tag}: think {tw} palavras > teto {tmax}")
        if not think_text(content):
            problems.append(f"{tag}: think vazio ou malformado")

        if layer == "0":
            if "<tool_call>" in content:
                problems.append(f"{tag}: camada 0 com tool call")
            low = content.lower()
            for mk in LAYER0_MARKERS:
                if mk in low:
                    problems.append(f"{tag}: marcador proibido {mk!r}")
        limit = layers[layer].get("preamble_max_words")
        if limit and layer == "0.5":
            pw = word_count(preamble_text(content))
            if pw > limit:
                problems.append(f"{tag}: preambulo {pw} palavras > teto {limit}")

        for pat in banned:
            if pat.search(content) or pat.search(user):
                problems.append(f"{tag}: giria proibida {pat.pattern!r}")

    if problems:
        print(f"\n{len(problems)} PROBLEMA(S):")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print(f"checagens locais OK em {len(rows)} exemplos")


def main():
    groups = [("batch_046", H, "H/camada 0"), ("batch_047", I, "I/camada C"),
              ("batch_048", J, "J/camada 0.5")]
    check(H + I + J)
    for name, rows, label in groups:
        path = GEN / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        pt = sum(1 for r in rows if r["lang"] == "pt-BR")
        print(f"{path.name}: {len(rows)} ({label}) — {pt} pt-BR / {len(rows) - pt} en")


if __name__ == "__main__":
    main()
