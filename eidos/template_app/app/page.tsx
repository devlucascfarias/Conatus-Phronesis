import Navbar from "@/components/Navbar";
import Card from "@/components/Card";
import Button from "@/components/Button";

const features = [
  {
    title: "Disciplina de terminal",
    description: "Instala antes de importar, builda depois de editar.",
  },
  {
    title: "Ciclo de correção",
    description: "Lê o stderr inteiro antes de reagir ao erro.",
  },
  {
    title: "Gosto visual",
    description: "Componentes com estados, dark mode e espaçamento generoso.",
  },
];

export default function Home() {
  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 sm:px-6">
        <section className="flex flex-col items-center gap-6 py-24 text-center">
          <h1 className="max-w-2xl text-4xl font-bold tracking-tight sm:text-5xl">
            App base do harness Eidos
          </h1>
          <p className="max-w-xl text-lg text-zinc-500 dark:text-zinc-400">
            Este projeto é o ponto de partida dos casos de avaliação: os
            componentes abaixo encarnam o guia de estilo.
          </p>
          <div className="flex items-center gap-3">
            <Button size="lg">Começar agora</Button>
            <Button size="lg" variant="secondary">
              Ver documentação
            </Button>
          </div>
        </section>
        <section
          id="recursos"
          className="grid grid-cols-1 gap-6 pb-24 sm:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((feature) => (
            <Card
              key={feature.title}
              title={feature.title}
              description={feature.description}
            />
          ))}
        </section>
      </main>
    </>
  );
}
