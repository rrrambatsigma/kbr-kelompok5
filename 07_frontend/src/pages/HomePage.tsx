import {
  ArrowRight,
  BadgeCheck,
  BookOpen,
  Database,
  Info,
  Leaf,
  SearchCheck,
  ShieldCheck,
  Sprout,
  Stethoscope,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { SectionHeading } from "../components/common/SectionHeading";
import { Spinner } from "../components/common/Spinner";
import { listDiseases } from "../services/api/diseases";
import { listPlants } from "../services/api/plants";
import type { DiseaseSummary, Plant } from "../types/api";

const workflow = [
  {
    icon: Sprout,
    step: "Langkah 01",
    title: "Informasi Tanaman",
    description:
      "Pilih komoditas yang akan diperiksa. Sistem memuat gejala yang relevan dari knowledge base.",
  },
  {
    icon: SearchCheck,
    step: "Langkah 02",
    title: "Identifikasi Gejala",
    description:
      "Pilih gejala yang terlihat di lapangan. Semakin banyak ciri yang sesuai, semakin terbantu proses penalaran.",
  },
  {
    icon: BadgeCheck,
    step: "Langkah 03",
    title: "Hasil dan Rekomendasi",
    description:
      "Lihat kandidat penyakit, skor kecocokan, bukti gejala, dan pengendalian yang tersedia di knowledge base.",
  },
];

const features = [
  {
    icon: Stethoscope,
    title: "Identifikasi Kemungkinan Penyakit",
    description:
      "Mesin reasoning mencocokkan gejala yang dipilih dengan pengetahuan penyakit pada tanaman.",
  },
  {
    icon: BookOpen,
    title: "Informasi Penyakit Tanaman",
    description:
      "Telusuri katalog penyakit, patogen, bagian tanaman terdampak, fase, dan faktor risiko.",
  },
  {
    icon: ShieldCheck,
    title: "Rekomendasi Pengendalian",
    description:
      "Pelajari tindakan pengendalian yang tercatat di sumber pengetahuan, bukan rekomendasi karangan.",
  },
];

function previewDiseases(
  diseases: DiseaseSummary[],
  plantId: string
): DiseaseSummary[] {
  return diseases
    .filter((disease) => disease.plantId === plantId)
    .slice(0, 3);
}

export function HomePage() {
  const [plants, setPlants] = useState<Plant[]>([]);
  const [diseases, setDiseases] = useState<DiseaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([listPlants(), listDiseases()])
      .then(([plantItems, diseaseItems]) => {
        if (cancelled) {
          return;
        }
        setPlants(plantItems);
        setDiseases(diseaseItems);
      })
      .catch(() => {
        if (!cancelled) {
          setError(
            "Data knowledge base belum dapat dimuat. Pastikan backend TaniCare berjalan."
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const featuredPlants = useMemo(() => {
    const preferred = ["Padi", "Jagung"];
    const selected = preferred
      .map((id) => plants.find((plant) => plant.id === id))
      .filter((plant): plant is Plant => plant !== undefined);
    return selected.length > 0 ? selected : plants.slice(0, 2);
  }, [plants]);

  return (
    <div>
      <section className="hero-pattern relative overflow-hidden border-b border-border">
        <div className="container-page grid items-center gap-12 py-16 lg:grid-cols-12 lg:py-24">
          <div className="animate-rise space-y-6 lg:col-span-7">
            <span className="eyebrow">
              <Leaf className="h-3.5 w-3.5" aria-hidden="true" />
              Sistem Pakar Penyakit Tanaman Pangan
            </span>
            <h1 className="text-balance font-heading text-4xl font-extrabold leading-[1.08] tracking-tight text-primary sm:text-5xl lg:text-6xl">
              Kenali Penyakit Tanaman, Temukan Langkah Pengendalian yang Tepat.
            </h1>
            <p className="max-w-2xl text-base leading-8 text-muted sm:text-lg">
              Bantu identifikasi kemungkinan penyakit tanaman pangan tropis
              berdasarkan gejala yang terlihat, melalui sistem berbasis
              pengetahuan yang dapat dijelaskan.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Link to="/diagnosis" className="btn-primary">
                Mulai Diagnosis
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link to="/knowledge-base" className="btn-secondary">
                <BookOpen className="h-4 w-4" aria-hidden="true" />
                Jelajahi Knowledge Base
              </Link>
            </div>
            <p className="flex items-center gap-2 text-xs text-muted">
              <ShieldCheck className="h-4 w-4 text-secondary" aria-hidden="true" />
              Informasi berbasis knowledge base • Membantu keputusan awal, bukan
              pengganti pemeriksaan ahli.
            </p>
          </div>

          <div className="relative lg:col-span-5">
            <div className="absolute -inset-6 -z-10 rounded-[2.5rem] bg-secondary/10 blur-2xl" />
            <div className="card overflow-hidden p-2">
              <div className="botanical-grid relative flex aspect-[4/3] flex-col justify-between overflow-hidden rounded-xl bg-gradient-to-br from-[#174b35] via-[#1d5f43] to-[#2f7a52] p-6 text-white">
                <svg
                  viewBox="0 0 400 300"
                  className="pointer-events-none absolute inset-0 h-full w-full opacity-25"
                  aria-hidden="true"
                >
                  <path
                    d="M-20 260C60 210 110 120 240 80c50-15 100-18 180-10"
                    fill="none"
                    stroke="#c4e19c"
                    strokeWidth="2"
                  />
                  <path
                    d="M40 280C100 220 150 150 280 110"
                    fill="none"
                    stroke="#a8c9a5"
                    strokeWidth="1.5"
                  />
                  <path d="M140 180c30-35 70-45 110-35-20 40-55 55-110 35Z" fill="#a8c9a5" />
                  <path d="M210 135c25-35 65-45 105-30-20 38-55 50-105 30Z" fill="#c4e19c" />
                </svg>
                <div className="relative flex items-center justify-between">
                  <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider">
                    Agroekosistem Tropis
                  </span>
                  <Leaf className="h-6 w-6 text-[#c4e19c]" aria-hidden="true" />
                </div>
                <div className="relative space-y-3">
                  <p className="max-w-xs font-heading text-2xl font-bold leading-tight">
                    Pengetahuan yang bisa ditelusuri, bukan kotak hitam.
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded-xl bg-white/10 p-3 backdrop-blur">
                      <p className="text-white/70">Tanaman</p>
                      <p className="mt-1 font-mono text-xl font-bold">
                        {error ? "—" : loading ? "…" : plants.length}
                      </p>
                    </div>
                    <div className="rounded-xl bg-white/10 p-3 backdrop-blur">
                      <p className="text-white/70">Penyakit</p>
                      <p className="mt-1 font-mono text-xl font-bold">
                        {error ? "—" : loading ? "…" : diseases.length}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="space-y-2 p-4 text-xs text-muted">
                <div className="flex items-center justify-between gap-3">
                  <span>Metode penalaran</span>
                  <span className="font-semibold text-primary">
                    Knowledge-Based Reasoning
                  </span>
                </div>
                <div className="h-px bg-border" />
                <div className="flex items-center justify-between gap-3">
                  <span>Status data</span>
                  <span className="flex items-center gap-1.5 font-semibold text-secondary">
                    <Database className="h-3.5 w-3.5" aria-hidden="true" />
                    {loading ? "Memuat…" : "Dari backend"}
                  </span>
                </div>
              </div>
            </div>
            {error && (
              <p className="mt-2 rounded-xl border border-warning/20 bg-[#fffaf5] px-3 py-2 text-xs text-warning">
                {error}
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="section-space border-b border-border bg-surface-low">
        <div className="container-page space-y-10">
          <SectionHeading
            eyebrow="Alur Kerja Sistem"
            title="Proses Identifikasi yang Mudah"
            description="Tiga langkah sederhana untuk memperoleh informasi kemungkinan penyakit tanaman pangan secara terstruktur."
          />
          <div className="grid gap-5 md:grid-cols-3">
            {workflow.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.title} className="card flex flex-col gap-5 p-6">
                  <div className="flex items-center justify-between">
                    <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-low text-primary">
                      <Icon className="h-6 w-6" aria-hidden="true" />
                    </span>
                    <span className="badge-neutral">{item.step}</span>
                  </div>
                  <div>
                    <h3 className="font-heading text-lg font-bold text-foreground">
                      {item.title}
                    </h3>
                    <p className="mt-2 text-sm leading-6 text-muted">
                      {item.description}
                    </p>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="section-space">
        <div className="container-page space-y-10">
          <SectionHeading
            eyebrow="Expert System"
            title="Fitur yang Membantu Anda"
            description="Dirancang untuk membantu penanganan kesehatan tanaman pangan tropis dengan informasi yang dapat ditelusuri."
          />
          <div className="grid gap-5 md:grid-cols-3">
            {features.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.title} className="card p-6">
                  <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-low text-primary">
                    <Icon className="h-6 w-6" aria-hidden="true" />
                  </span>
                  <h3 className="mt-5 font-heading text-lg font-bold text-foreground">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-muted">
                    {item.description}
                  </p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="section-space bg-surface-low">
        <div className="container-page">
          <div className="card grid gap-8 p-6 sm:p-10 lg:grid-cols-12">
            <div className="space-y-4 lg:col-span-5">
              <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-secondary">
                Katalog Pengetahuan
              </p>
              <h2 className="font-heading text-3xl font-bold tracking-tight text-primary">
                Kenali lebih banyak penyakit tanaman
              </h2>
              <p className="text-sm leading-7 text-muted">
                Telusuri penyakit dari tujuh komoditas, lengkap dengan gejala,
                patogen, bagian terdampak, dan pengendalian yang tercatat.
              </p>
              <Link to="/knowledge-base" className="btn-primary w-fit">
                Jelajahi Knowledge Base
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:col-span-7">
              {loading && (
                <div className="sm:col-span-2">
                  <Spinner label="Memuat preview knowledge base" />
                </div>
              )}
              {!loading &&
                featuredPlants.map((plant) => {
                  const items = previewDiseases(diseases, plant.id);
                  return (
                    <article key={plant.id} className="card p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <span className="badge-neutral">Tanaman Pangan</span>
                          <h3 className="mt-3 font-heading text-xl font-bold text-primary">
                            {plant.label}
                          </h3>
                          <p className="mt-1 text-xs italic text-muted">
                            {plant.scientificName ?? "Nama ilmiah belum tersedia"}
                          </p>
                        </div>
                        <Leaf className="h-5 w-5 text-secondary" aria-hidden="true" />
                      </div>
                      <div className="mt-4 border-t border-border pt-4">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                          Penyakit dalam katalog
                        </p>
                        <ul className="mt-2 space-y-2">
                          {items.map((disease) => (
                            <li
                              key={disease.id}
                              className="flex items-start gap-2 text-sm text-foreground"
                            >
                              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary" />
                              <span>{disease.label}</span>
                            </li>
                          ))}
                          {items.length === 0 && (
                            <li className="text-sm text-muted">
                              Belum ada penyakit untuk tanaman ini.
                            </li>
                          )}
                        </ul>
                      </div>
                      <Link
                        to="/knowledge-base"
                        className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-secondary hover:text-primary"
                      >
                        Buka katalog
                        <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                      </Link>
                    </article>
                  );
                })}
            </div>
          </div>
        </div>
      </section>

      <section id="tentang" className="section-space pt-0">
        <div className="container-page">
          <div className="card flex flex-col gap-4 border-border bg-surface-low p-6 sm:flex-row sm:items-start">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-container text-white">
              <Info className="h-5 w-5" aria-hidden="true" />
            </span>
            <div>
              <h2 className="font-heading text-base font-bold text-foreground">
                Informasi penting
              </h2>
              <p className="mt-1 text-sm leading-7 text-muted">
                Hasil identifikasi merupakan kemungkinan penyakit berdasarkan
                informasi yang dimasukkan dan pengetahuan yang tersedia. Hasil
                ini adalah informasi pendukung keputusan awal, bukan pengganti
                pemeriksaan langsung oleh ahli agronomi atau penyuluh pertanian.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
