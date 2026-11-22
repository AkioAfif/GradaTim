import UserAvatar from "../UserAvatar";

export const TOTAL_LANGKAH = 5;

const NAMA_LANGKAH = ["Goal", "Kegiatan Rutin", "Rencana AI", "Tinjau Rencana", "Jadwalkan"];

/** Header halaman wizard: breadcrumb, avatar, penanda langkah, judul. */
export default function WizardHeader({
  langkah,
  judul,
  subjudul,
}: {
  langkah: number;
  judul: string;
  subjudul: string;
}) {
  return (
    <>
      <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
        <p className="text-xs text-[#8B857B]">Perencanaan / {NAMA_LANGKAH[langkah - 1]}</p>
        <UserAvatar />
      </header>

      <section className="mt-7">
        <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">
          LANGKAH {langkah} DARI {TOTAL_LANGKAH}
        </p>

        <ol className="mt-3 flex gap-1.5" aria-label="Progres wizard">
          {NAMA_LANGKAH.map((nama, index) => (
            <li
              key={nama}
              title={nama}
              aria-current={index + 1 === langkah ? "step" : undefined}
              className={`h-1.5 flex-1 rounded-full ${
                index + 1 <= langkah ? "bg-[#82947B]" : "bg-[#E5DFD3]"
              }`}
            />
          ))}
        </ol>

        <h1 className="mt-4 text-3xl font-medium tracking-tight md:text-4xl">{judul}</h1>
        <p className="mt-3 text-sm text-[#8B857B]">{subjudul}</p>
      </section>
    </>
  );
}
