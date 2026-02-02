"use client";

import { createContext, type ReactNode, useContext } from "react";
import { useSession } from "@/lib/auth-client";

interface User {
  id: string;
  name: string;
  email: string;
  image?: string | null;
}

interface UserContextValue {
  user: User | null;
  isLoading: boolean;
}

const UserContext = createContext<UserContextValue>({
  user: null,
  isLoading: true,
});

export function UserProvider({ children }: { children: ReactNode }) {
  const { data: session, isPending } = useSession();

  const user = session?.user
    ? {
        id: session.user.id,
        name: session.user.name || session.user.email?.split("@")[0] || "User",
        email: session.user.email || "",
        image: session.user.image,
      }
    : null;

  return (
    <UserContext.Provider value={{ user, isLoading: isPending }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}

/**
 * Get initials from a name
 * Handles both "First Last" and "Last, First" formats
 * e.g., "Jason Matherly" -> "JM", "Matherly, Jason" -> "JM"
 */
export function getInitials(name: string): string {
  if (!name) return "U";

  let firstName: string;
  let lastName: string;

  // Check for "Last, First" format (common in Microsoft/corporate systems)
  if (name.includes(",")) {
    const [last, first] = name.split(",").map((s) => s.trim());
    firstName = first || "";
    lastName = last || "";
  } else {
    // "First Last" format
    const parts = name.trim().split(/\s+/);
    firstName = parts[0] || "";
    lastName = parts.length > 1 ? parts[parts.length - 1] : "";
  }

  if (!firstName && !lastName) return "U";
  if (!lastName) return firstName.charAt(0).toUpperCase();
  if (!firstName) return lastName.charAt(0).toUpperCase();

  return (firstName.charAt(0) + lastName.charAt(0)).toUpperCase();
}
