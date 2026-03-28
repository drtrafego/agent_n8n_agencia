'use client';

import Link from 'next/link';
import { useState, Suspense } from 'react';
import { usePathname } from 'next/navigation';
import { MessageSquare, Settings, LogOut, Bot, BarChart3, Kanban, Activity, Cpu } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { signOut } from '@/app/(login)/actions';
import { useRouter } from 'next/navigation';
import { User } from '@/lib/db/schema';
import useSWR, { mutate } from 'swr';
import { cn } from '@/lib/utils';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

const NAV_ITEMS = [
  { href: '/inbox', label: 'Inbox', icon: MessageSquare },
  { href: '/crm', label: 'CRM', icon: Kanban },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/tokens', label: 'Tokens', icon: Cpu },
  { href: '/logs', label: 'Logs', icon: Activity },
  { href: '/settings', label: 'Config', icon: Settings },
];

function UserMenu() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { data: user } = useSWR<User>('/api/user', fetcher);
  const router = useRouter();

  async function handleSignOut() {
    await signOut();
    mutate('/api/user');
    router.push('/');
  }

  const initials = user?.name
    ? user.name.split(' ').slice(0, 2).map((n) => n[0]).join('').toUpperCase()
    : user?.email?.[0].toUpperCase() ?? '?';

  return (
    <DropdownMenu open={isMenuOpen} onOpenChange={setIsMenuOpen}>
      <DropdownMenuTrigger>
        <Avatar className="cursor-pointer size-8">
          <AvatarImage alt={user?.name || ''} />
          <AvatarFallback className="bg-indigo-600 text-white text-xs">
            {initials}
          </AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="flex flex-col gap-1 bg-zinc-900 border-zinc-800">
        <div className="px-2 py-1.5 border-b border-zinc-800 mb-1">
          <p className="text-xs font-medium text-zinc-200">{user?.name || 'Usuário'}</p>
          <p className="text-[10px] text-zinc-500">{user?.email}</p>
        </div>
        <form action={handleSignOut} className="w-full">
          <button type="submit" className="flex w-full">
            <DropdownMenuItem className="w-full flex-1 cursor-pointer text-zinc-400 hover:text-zinc-100">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Sair</span>
            </DropdownMenuItem>
          </button>
        </form>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function Header() {
  const pathname = usePathname();

  return (
    <header className="flex h-[57px] items-center justify-between border-b border-zinc-800 bg-zinc-950 px-4">
      {/* Logo */}
      <Link href="/inbox" className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600">
          <Bot size={14} className="text-white" />
        </div>
        <span className="text-sm font-semibold text-zinc-100">Agente 24 Horas</span>
      </Link>

      {/* Nav desktop */}
      <nav className="hidden md:flex items-center gap-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              pathname.startsWith(href)
                ? 'bg-zinc-800 text-zinc-100'
                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
            )}
          >
            <Icon size={14} />
            {label}
          </Link>
        ))}
      </nav>

      {/* User */}
      <Suspense fallback={<div className="h-8 w-8 rounded-full bg-zinc-800" />}>
        <UserMenu />
      </Suspense>
    </header>
  );
}

function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex border-t border-zinc-800 bg-zinc-950">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
        <Link
          key={href}
          href={href}
          className={cn(
            'flex flex-1 flex-col items-center justify-center gap-1 py-3 text-[10px] font-medium transition-colors',
            pathname.startsWith(href)
              ? 'text-indigo-400'
              : 'text-zinc-600 hover:text-zinc-400'
          )}
        >
          <Icon size={20} />
          {label}
        </Link>
      ))}
    </nav>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen bg-zinc-950 text-zinc-100">
      <Header />
      <main className="flex-1 pb-[57px] md:pb-0">{children}</main>
      <BottomNav />
    </div>
  );
}
