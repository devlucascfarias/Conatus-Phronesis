# Guia de estilo visual — Conatus Eidos

O "elegante e moderno" do Eidos não é opinião: é este checklist. Os componentes do
`template_app` (Button, Card, Navbar) são a referência viva — todo componente novo,
gerado pelo modelo ou escrito num exemplo de treino, deve passar nos itens abaixo.
Os checks automáticos dos casos `create-component` derivam daqui.

## 1. Forma e superfície

- **Cantos:** `rounded-xl` para elementos interativos (botões, inputs), `rounded-2xl`
  para superfícies (cards, modais). Nunca misturar raios diferentes num mesmo componente.
- **Bordas e sombras:** superfícies têm definição — `border` sutil (`zinc-200`/`zinc-800`)
  + `shadow-sm`, elevando pra `shadow-md` no hover quando o elemento é clicável.
- **Espaçamento generoso:** `p-6` mínimo em cards, `gap-4`+ entre itens de grid,
  seções com `py-16`+. Conteúdo nunca encosta na borda do viewport: container com `px-4 sm:px-6`.

## 2. Tipografia

- Títulos: `font-semibold`/`font-bold` + `tracking-tight`.
- Corpo: `text-sm`/`text-base`; texto secundário SEMPRE em cor rebaixada
  (`text-zinc-500 dark:text-zinc-400`), nunca em cinza claro sobre fundo claro.
- Hierarquia por peso e cor, não por tamanho exagerado. Nada de `text-justify`.

## 3. Cor

- Base neutra: escala `zinc` (ou `slate`, mas uma só por projeto).
- **Dark mode é obrigatório**: todo componente tem variantes `dark:` (o template usa
  `darkMode: "class"`). Fundo claro `bg-white`/`zinc-50`, escuro `zinc-900`/`zinc-950`.
- Cor de destaque com parcimônia: uma por tela (CTA primário, estado de sucesso/erro).
- Semântica: verde = positivo, vermelho = negativo/destrutivo, âmbar = atenção.

## 4. Estados (o que separa componente vivo de mockup)

- **Todo elemento interativo tem os 4:** `hover:` (mudança de cor/fundo),
  `focus-visible:ring-2` (nunca remover o focus sem substituir), `disabled:opacity-50`
  + `disabled:pointer-events-none`, e transição — `transition-colors duration-150`
  (interação rápida) ou `duration-200`/`300` (superfícies).
- Movimento discreto: transições de cor/sombra/opacidade. Nada de bounce, spin ou
  animação chamativa sem pedido explícito.

## 5. Acessibilidade mínima

- Tags semânticas: `header`/`nav`/`main`/`section`/`footer`, `button` para ação,
  `a`/`Link` para navegação.
- Botão só-ícone SEMPRE com `aria-label`.
- Inputs com `label` associado (ou `aria-label`).
- Imagens com `alt` descritivo.

## 6. Código do componente

- TypeScript estrito: props tipadas (`type XProps = {...}`), sem `any`.
- `export default` no componente principal do arquivo; um componente por arquivo.
- Compor classes com `cn()` de `@/lib/utils` quando há condicionais.
- `"use client"` APENAS quando há estado/efeito/evento — server component é o padrão.
- Responsivo mobile-first: layout base pro mobile, `sm:`/`lg:` expandem.
