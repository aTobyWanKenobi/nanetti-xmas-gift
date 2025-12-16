import { useState, useEffect } from "react";
import Login from "./components/Login";
import EmotionSelector from "./components/EmotionSelector";
import PhotoDisplay from "./components/PhotoDisplay"; // Note: Ensure this path is correct
import { AnimatePresence } from "framer-motion";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loadingAuth, setLoadingAuth] = useState(true);
  const [currentEmotion, setCurrentEmotion] = useState(null);

  const [buffer, setBuffer] = useState({
    happy: [],
    romantic: [],
    sad: [],
    angry: []
  });

  // Helper to pre-fetch an image so it's in browser cache
  const preloadImage = (url) => {
    const img = new Image();
    img.src = url;
  };

  // Helper to replenish buffer for a specific emotion
  const fillBuffer = (emotionId) => {
    fetch(`/api/draw/${emotionId}`)
      .then(res => res.json())
      .then(data => {
        // Preload the actual image bytes
        if (data.photo_url) {
          preloadImage(data.photo_url);
        }

        setBuffer(prev => ({
          ...prev,
          [emotionId]: [...prev[emotionId], data]
        }));
      })
      .catch(err => console.error("Buffer fill failed:", err));
  };

  useEffect(() => {
    // Check initial auth state
    fetch("/api/check-auth")
      .then((res) => res.json())
      .then((data) => {
        setIsAuthenticated(data.authenticated);
        setLoadingAuth(false);
      })
      .catch(() => {
        // Assume unauthenticated on error (dev mode or network error)
        setIsAuthenticated(false);
        setLoadingAuth(false);
      });
  }, []);

  // Initial fill on login
  useEffect(() => {
    if (isAuthenticated) {
      ['happy', 'romantic', 'sad', 'angry'].forEach(id => {
        fillBuffer(id);
      });
    }
  }, [isAuthenticated]);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleSelectEmotion = (id) => {
    // Check buffer
    const nextItem = buffer[id][0];

    if (nextItem) {
      // Use buffered item
      setCurrentEmotion({ id, data: nextItem });
      // Remove from buffer and replenish
      setBuffer(prev => ({
        ...prev,
        [id]: prev[id].slice(1)
      }));
      fillBuffer(id);
    } else {
      // Fallback: Set emotion without data (Display will fetch)
      setCurrentEmotion({ id, data: null });
      // Also trigger a fill for next time
      fillBuffer(id);
    }
  };

  const handleComplete = () => {
    setCurrentEmotion(null);
  };

  if (loadingAuth) {
    return null; // Or spinner
  }

  return (
    <div className="app-content">
      <AnimatePresence mode="wait">
        {!isAuthenticated ? (
          <Login key="login" onLogin={handleLogin} />
        ) : !currentEmotion ? (
          <EmotionSelector key="selector" onSelect={handleSelectEmotion} />
        ) : (
          <PhotoDisplay
            key="photo"
            emotionId={currentEmotion.id}
            initialData={currentEmotion.data}
            onComplete={handleComplete}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
