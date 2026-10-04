import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Spinner from "./components/Spinner";
import { useAuth } from "./lib/auth";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import Onboarding from "./pages/Onboarding";
import Portfolio from "./pages/Portfolio";
import Recommendations from "./pages/Recommendations";

function RequireAuth({ children, needsProfile = true }) {
  const { user, loading } = useAuth();
  if (loading) return <Spinner full />;
  if (!user) return <Navigate to="/login" replace />;
  if (needsProfile && !user.profile) return <Navigate to="/onboarding" replace />;
  return children;
}

function Home() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner full />;
  return <Navigate to={!user ? "/login" : user.profile ? "/dashboard" : "/onboarding"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/signup" element={<AuthPage mode="signup" />} />
      <Route path="/onboarding" element={<RequireAuth needsProfile={false}><Onboarding /></RequireAuth>} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/recommendations" element={<Recommendations />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
