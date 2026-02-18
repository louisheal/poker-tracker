import "./App.css";

import { ThemeProvider } from "@/components/theme-provider";
import { AppSidebar } from "./components/app-sidebar";
import { SidebarInset, SidebarProvider } from "./components/ui/sidebar";

function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset></SidebarInset>
      </SidebarProvider>
    </ThemeProvider>
  );
}

export default App;
