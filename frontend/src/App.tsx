import "./App.css";

import { ThemeProvider } from "@/components/theme-provider";
import { Ranges } from "./views/Ranges";

function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <Ranges />
    </ThemeProvider>
  );
}

export default App;
