import { Press_Start_2P, VT323 } from 'next/font/google';
import './globals.css';
import Providers from './providers';
import NavBar from '@/components/NavBar';

const pressStart = Press_Start_2P({
  subsets: ['latin'],
  weight: '400',
  variable: '--font-press-start',
  display: 'swap',
});

const vt323 = VT323({
  subsets: ['latin'],
  weight: '400',
  variable: '--font-vt323',
  display: 'swap',
});

export const metadata = {
  title: 'CodeCrypt: The AI Dungeon',
  description: 'An adaptive learning RPG where your real knowledge powers your character.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${pressStart.variable} ${vt323.variable}`}>
      <body>
        <Providers>
          <NavBar />
          <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
