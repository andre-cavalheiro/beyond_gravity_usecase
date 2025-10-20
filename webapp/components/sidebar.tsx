"use client";

import Link from "next/link";
import clsx from "clsx";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useTheme } from "next-themes";
import { Home, Menu, ChevronsLeft, ChevronsRight, Sun, Moon, LogOut, ChevronsUpDown } from "lucide-react";

import { useAuth } from "@/lib/auth/context"
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { DropdownMenu,DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

export function Sidebar() {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { userAuth, signOut } = useAuth();
  const { theme, setTheme } = useTheme();
  const pathname = usePathname();

  const navItems = [
    { href: "/home", label: "Home", icon: Home }
  ];

  const SidebarContent = (
    <div
      className={clsx(
        "h-full border-r border-border bg-muted/20 flex flex-col justify-between transition-all duration-300",
        collapsed ? "w-16 items-center" : "w-54"
      )}
    >
      <div
        className={clsx(
          "w-full flex items-center justify-between px-3 py-3",
          collapsed && "justify-center px-0"
        )}
      >
        {/* Product Name */}
        <div className={clsx("transition-all", collapsed && "hidden")}>
          <h1 className="text-lg font-semibold leading-tight text-foreground">
            Beyond Gravity
          </h1>
          <p className="text-xs text-muted-foreground -mt-0.5">Earthquake Monitoring</p>
        </div>

        {/* Collapse Toggle */}
        <Button
          size="icon"
          variant="ghost"
          className={clsx(
            "transition-all ml-auto",
            collapsed && "mx-auto"
          )}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
        </Button>
      </div>
      
      <DropdownMenuSeparator />

      {/* Nav */}
      <ScrollArea className="flex-1 w-full px-2">
        <nav className="flex flex-col gap-2">
          {navItems.map(({ href, label, icon: Icon }) => (
            <Link href={href} key={href}>
              <Button
                variant={pathname === href ? "secondary" : "ghost"}
                className={clsx(
                  "w-full justify-start",
                  collapsed ? "px-2 justify-center" : "px-4",
                  pathname === href && "bg-muted font-semibold"
                )}
              >
                <Icon className="h-5 w-5" />
                {!collapsed && <span className="ml-2">{label}</span>}
              </Button>

            </Link>
          ))}
        </nav>
      </ScrollArea>

      {/* Bottom user/avatar menu */}
      <div className="px-2 pb-4">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className={clsx(
                  "w-full flex items-center gap-3 rounded-lg px-3 py-2",
                  "hover:bg-muted transition-colors",
                  "focus-visible:ring-0 focus-visible:ring-offset-0",
                  collapsed && "justify-center px-0"
                )}
              >
              <Avatar className="h-8 w-8">
                {userAuth?.photoURL ? (
                  <AvatarImage src={userAuth.photoURL} alt={userAuth.displayName ?? "User"} />
                ) : (
                  <AvatarFallback>
                    {process.env.NEXT_PUBLIC_SKIP_AUTH === "true"
                      ? "X"
                      : userAuth?.displayName?.[0]?.toUpperCase() ?? "?"}
                  </AvatarFallback>
                )}
              </Avatar>

              {!collapsed && (
                <div className="flex flex-col truncate">
                  <span className="text-sm font-medium leading-none truncate">
                    {userAuth?.displayName ?? "Mock User"}
                  </span>
                  <span className="text-xs text-muted-foreground truncate max-w-[140px]">
                    {userAuth?.email ?? "mock@example.com"}
                  </span>
                </div>
              )}

              {!collapsed && (
                <ChevronsUpDown className="h-4 w-4 text-muted-foreground ml-auto" />
              )}
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent className="w-64 p-2" align="end" sideOffset={8}>
            <div className="flex items-center gap-2 p-2">
              <Avatar className="h-10 w-10">
                {userAuth?.photoURL ? (
                  <AvatarImage src={userAuth.photoURL} alt="User" />
                ) : (
                  <AvatarFallback>
                    {process.env.NEXT_PUBLIC_SKIP_AUTH === "true"
                      ? "X"
                      : userAuth?.displayName?.[0]?.toUpperCase() ?? "?"}
                  </AvatarFallback>
                )}
              </Avatar>
              <div className="space-y-1">
                <p className="text-sm font-medium leading-none">
                  {userAuth?.displayName ?? "Mock User"}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {userAuth?.email ?? "mock@example.com"}
                </p>
              </div>
            </div>

            <DropdownMenuSeparator />
            
            {/* Theme */}
            <DropdownMenuItem
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? (
                <>
                  <Sun className="mr-2 h-4 w-4" />
                  Light Mode
                </>
              ) : (
                <>
                  <Moon className="mr-2 h-4 w-4" />
                  Dark Mode
                </>
              )}
            </DropdownMenuItem>
            
            {/* Sign-Out */}
            <DropdownMenuItem
              onClick={() => signOut()}
              className="text-destructive focus:text-destructive"
            >
              <LogOut className="mr-2 h-4 w-4" />
              Log out
            </DropdownMenuItem>

          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex">{SidebarContent}</aside>

      {/* Mobile toggle button + Sheet */}
      <div className="md:hidden absolute top-4 left-4 z-50">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button size="icon" variant="ghost">
              <Menu className="w-5 h-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-48">
            {SidebarContent}
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
