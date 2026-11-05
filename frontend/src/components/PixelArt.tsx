import type { ReactElement } from "react";
import type { Speaker } from "../types";

interface PixelProps {
  rows: string[];
  palette: Record<string, string>;
  className?: string;
}

export function PixelArt({ rows, palette, className }: PixelProps) {
  const h = rows.length;
  const w = rows[0].length;
  const cells: ReactElement[] = [];
  rows.forEach((row, y) => {
    Array.from(row).forEach((ch, x) => {
      const fill = palette[ch];
      if (fill) cells.push(<rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill={fill} />);
    });
  });
  return (
    <svg className={className} viewBox={`0 0 ${w} ${h}`} shapeRendering="crispEdges" aria-hidden="true" focusable="false">
      {cells}
    </svg>
  );
}

const PERSON = [
  "...hhhh...",
  "..hhhhhh..",
  "..hssssh..",
  "..skssks..",
  "..ssssss..",
  "...ssss...",
  ".bbbbbbbb.",
  "bbbwwwwbbb",
  "bbbbbbbbbb",
  "bbbbddbbbb",
  ".bbbbbbbb.",
  ".dd....dd."
];

const INK = "#1d120a";
const SKIN = "#f1c9a0";

export const PALETTES: Record<Speaker, Record<string, string>> = {
  judge: { h: "#e8e0d0", s: SKIN, k: INK, b: "#2a1a10", d: "#6b4226", w: "#f3e2b3" },
  jury: { h: "#5a3a1e", s: SKIN, k: INK, b: "#5b7fb0", d: "#35507a", w: "#f3e2b3" },
  defense: { h: "#3b2314", s: SKIN, k: INK, b: "#3a5f9e", d: "#223a66", w: "#ffffff" },
  prosecution: { h: "#1d120a", s: SKIN, k: INK, b: "#b3261e", d: "#6e130f", w: "#ffffff" },
  user: { h: "#a0521e", s: SKIN, k: INK, b: "#f4c542", d: "#c58b13", w: "#ffffff" }
};

const JURY_COATS = ["#5b7fb0", "#4f8a3c", "#8a5aa0", "#c58b13"];

export function Person({ speaker, seat = 0, className }: { speaker: Speaker; seat?: number; className?: string }) {
  const palette = speaker === "jury" ? { ...PALETTES.jury, b: JURY_COATS[seat % 4] } : PALETTES[speaker];
  return <PixelArt rows={PERSON} palette={palette} className={className} />;
}

const COURTHOUSE = [
  "......rrrr......",
  "....rrrrrrrr....",
  "..rrrrrrrrrrrr..",
  ".yyyyyyyyyyyyyy.",
  "..w.w.w..w.w.w..",
  "..w.w.w..w.w.w..",
  "..w.w.w..w.w.w..",
  "..w.w.w..w.w.w..",
  "..w.w.w..w.w.w..",
  ".yyyyyyyyyyyyyy.",
  "yyyyyyyyyyyyyyyy",
  "nnnnnnnnnnnnnnnn"
];

export function Courthouse({ className }: { className?: string }) {
  return <PixelArt rows={COURTHOUSE} palette={{ r: "#b3261e", y: "#f4c542", w: "#f3e2b3", n: "#6b4226" }} className={className} />;
}

const SCALES = [
  "....yyyy....",
  ".....yy.....",
  "yyyyyyyyyyyy",
  "y....yy....y",
  "y....yy....y",
  "yy...yy...yy",
  "yyy..yy..yyy",
  ".....yy.....",
  ".....yy.....",
  "....yyyy....",
  "...yyyyyy..."
];

export function Scales({ className }: { className?: string }) {
  return <PixelArt rows={SCALES} palette={{ y: "#f4c542" }} className={className} />;
}
