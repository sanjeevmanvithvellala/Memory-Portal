import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Badge } from './components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar';
import { ScrollArea } from './components/ui/scroll-area';
import { Separator } from './components/ui/separator';
import { Heart, MessageCircle, Upload, User, Video, Image, Mic, Send, Clock, CheckCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [userProfile, setUserProfile] = useState(null);
  const [memories, setMemories] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [avatarStatus, setAvatarStatus] = useState({});
  const [activeTab, setActiveTab] = useState('memories');
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  // Default user ID for demo (in production, this would come from authentication)
  const userId = 'demo_user_1';

  useEffect(() => {
    initializeUser();
    loadMemories();
    loadChatHistory();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const initializeUser = async () => {
    try {
      // Try to get existing profile
      const response = await axios.get(`${API}/profiles/${userId}`);
      setUserProfile(response.data);
    } catch (error) {
      if (error.response?.status === 404) {
        // Create default profile
        const newProfile = {
          name: 'My Loved One',
          personality_traits: 'Loving, caring, always supportive, had a great sense of humor and loved spending time with family.',
          avatar_image_url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=400&fit=crop&crop=face'
        };
        
        const createResponse = await axios.post(`${API}/profiles`, {
          ...newProfile,
          id: userId
        });
        setUserProfile(createResponse.data);
      }
    }
  };

  const loadMemories = async () => {
    try {
      const response = await axios.get(`${API}/memories/${userId}`);
      setMemories(response.data);
    } catch (error) {
      console.error('Error loading memories:', error);
    }
  };

  const loadChatHistory = async () => {
    try {
      const response = await axios.get(`${API}/chat/${userId}`);
      setChatMessages(response.data);
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!currentMessage.trim()) return;

    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/chat`, {
        user_id: userId,
        message: currentMessage
      });

      setChatMessages(prev => [
        ...prev,
        response.data.user_message,
        response.data.ai_response
      ]);
      
      setCurrentMessage('');
      
      // Create avatar video for the AI response
      if (userProfile?.avatar_image_url) {
        createAvatarVideo(response.data.ai_response.message);
      }
      
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createAvatarVideo = async (text) => {
    if (!userProfile?.avatar_image_url) return;
    
    try {
      const response = await axios.post(`${API}/avatar/create`, {
        user_id: userId,
        image_url: userProfile.avatar_image_url,
        text: text
      });
      
      const talkId = response.data.talk_id;
      setAvatarStatus(prev => ({ ...prev, [talkId]: 'created' }));
      
      // Poll for completion
      pollAvatarStatus(talkId);
      
    } catch (error) {
      console.error('Error creating avatar video:', error);
    }
  };

  const pollAvatarStatus = async (talkId) => {
    const maxAttempts = 30;
    let attempts = 0;
    
    const poll = async () => {
      try {
        const response = await axios.get(`${API}/avatar/${talkId}/status`);
        const status = response.data.status;
        
        setAvatarStatus(prev => ({ 
          ...prev, 
          [talkId]: {
            status,
            result_url: response.data.result_url
          }
        }));
        
        if (status === 'done' || status === 'error' || attempts >= maxAttempts) {
          return;
        }
        
        attempts++;
        setTimeout(poll, 2000);
        
      } catch (error) {
        console.error('Error polling avatar status:', error);
      }
    };
    
    poll();
  };

  const handleMemoryUpload = async (type) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = type === 'photo' ? 'image/*' : type === 'audio' ? 'audio/*' : '*/*';
    
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      
      const formData = new FormData();
      formData.append('user_id', userId);
      formData.append('type', type);
      formData.append('file', file);
      formData.append('description', `${type} memory: ${file.name}`);
      
      try {
        setIsLoading(true);
        await axios.post(`${API}/memories/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        loadMemories();
      } catch (error) {
        console.error('Error uploading memory:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    input.click();
  };

  const handleTextMemorySubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const content = formData.get('content');
    const description = formData.get('description');
    
    if (!content.trim()) return;
    
    try {
      setIsLoading(true);
      await axios.post(`${API}/memories`, {
        user_id: userId,
        type: 'text',
        content,
        description
      });
      loadMemories();
      e.target.reset();
    } catch (error) {
      console.error('Error creating text memory:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getMemoryIcon = (type) => {
    switch (type) {
      case 'photo': return <Image className="w-4 h-4" />;
      case 'audio': return <Mic className="w-4 h-4" />;
      default: return <MessageCircle className="w-4 h-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-purple-50 to-indigo-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-rose-200 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-gradient-to-r from-rose-500 to-purple-600 rounded-full">
                <Heart className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-rose-600 to-purple-600 bg-clip-text text-transparent">
                  Memory Portal
                </h1>
                <p className="text-sm text-gray-600">Reconnect with cherished memories</p>
              </div>
            </div>
            
            {userProfile && (
              <div className="flex items-center space-x-3">
                <Avatar className="w-10 h-10 border-2 border-rose-200">
                  <AvatarImage src={userProfile.avatar_image_url} />
                  <AvatarFallback><User className="w-5 h-5" /></AvatarFallback>
                </Avatar>
                <div className="text-right">
                  <p className="font-semibold text-gray-800">{userProfile.name}</p>
                  <p className="text-sm text-gray-500">Always in your heart</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 bg-white/60 backdrop-blur-sm">
            <TabsTrigger value="memories" className="flex items-center space-x-2">
              <Heart className="w-4 h-4" />
              <span>Memories</span>
            </TabsTrigger>
            <TabsTrigger value="chat" className="flex items-center space-x-2">
              <MessageCircle className="w-4 h-4" />
              <span>Conversation</span>
            </TabsTrigger>
            <TabsTrigger value="avatar" className="flex items-center space-x-2">
              <Video className="w-4 h-4" />
              <span>Avatar Videos</span>
            </TabsTrigger>
          </TabsList>

          {/* Memories Tab */}
          <TabsContent value="memories" className="space-y-6">
            <Card className="bg-white/60 backdrop-blur-sm border-rose-200">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Heart className="w-5 h-5 text-rose-500" />
                  <span>Add New Memory</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Button 
                    onClick={() => handleMemoryUpload('photo')}
                    className="flex items-center space-x-2 bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-600 hover:to-pink-600"
                    disabled={isLoading}
                  >
                    <Image className="w-4 h-4" />
                    <span>Upload Photo</span>
                  </Button>
                  
                  <Button 
                    onClick={() => handleMemoryUpload('audio')}
                    className="flex items-center space-x-2 bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600"
                    disabled={isLoading}
                  >
                    <Mic className="w-4 h-4" />
                    <span>Upload Audio</span>
                  </Button>
                  
                  <Button 
                    onClick={() => document.getElementById('text-memory-form').scrollIntoView()}
                    className="flex items-center space-x-2 bg-gradient-to-r from-indigo-500 to-blue-500 hover:from-indigo-600 hover:to-blue-600"
                  >
                    <MessageCircle className="w-4 h-4" />
                    <span>Write Memory</span>
                  </Button>
                </div>

                <form id="text-memory-form" onSubmit={handleTextMemorySubmit} className="space-y-4 pt-4 border-t border-rose-200">
                  <Input
                    name="description"
                    placeholder="Memory title (optional)"
                    className="border-rose-200 focus:border-rose-400"
                  />
                  <Textarea
                    name="content"
                    placeholder="Share a cherished memory..."
                    className="min-h-[100px] border-rose-200 focus:border-rose-400"
                    required
                  />
                  <Button 
                    type="submit" 
                    disabled={isLoading}
                    className="bg-gradient-to-r from-rose-500 to-purple-500 hover:from-rose-600 hover:to-purple-600"
                  >
                    Save Memory
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Memories List */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {memories.map((memory) => (
                <Card key={memory.id} className="bg-white/60 backdrop-blur-sm border-rose-200 hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="flex items-center space-x-1">
                        {getMemoryIcon(memory.type)}
                        <span className="capitalize">{memory.type}</span>
                      </Badge>
                      <span className="text-sm text-gray-500">
                        {formatDate(memory.created_at)}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-700 mb-2">{memory.description}</p>
                    {memory.type === 'text' && (
                      <p className="text-gray-800">{memory.content}</p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Chat Tab */}
          <TabsContent value="chat" className="space-y-6">
            <Card className="bg-white/60 backdrop-blur-sm border-rose-200">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <MessageCircle className="w-5 h-5 text-purple-500" />
                  <span>Conversation</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-96 w-full pr-4">
                  <div className="space-y-4">
                    {chatMessages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${message.is_user ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[80%] p-3 rounded-lg ${
                            message.is_user
                              ? 'bg-gradient-to-r from-rose-500 to-purple-500 text-white'
                              : 'bg-white border border-rose-200'
                          }`}
                        >
                          <p className="text-sm">{message.message}</p>
                          <p className={`text-xs mt-1 ${message.is_user ? 'text-rose-100' : 'text-gray-500'}`}>
                            {formatDate(message.timestamp)}
                          </p>
                        </div>
                      </div>
                    ))}
                    <div ref={chatEndRef} />
                  </div>
                </ScrollArea>

                <Separator className="my-4" />

                <div className="flex space-x-2">
                  <Input
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    placeholder="Share your thoughts..."
                    className="border-rose-200 focus:border-rose-400"
                    onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                    disabled={isLoading}
                  />
                  <Button
                    onClick={handleSendMessage}
                    disabled={isLoading || !currentMessage.trim()}
                    className="bg-gradient-to-r from-rose-500 to-purple-500 hover:from-rose-600 hover:to-purple-600"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Avatar Videos Tab */}
          <TabsContent value="avatar" className="space-y-6">
            <Card className="bg-white/60 backdrop-blur-sm border-rose-200">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Video className="w-5 h-5 text-indigo-500" />
                  <span>Avatar Videos</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {Object.keys(avatarStatus).length === 0 ? (
                  <div className="text-center py-8">
                    <Video className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">Start a conversation to see avatar videos</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Object.entries(avatarStatus).map(([talkId, status]) => (
                      <Card key={talkId} className="bg-white border-rose-200">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <Video className="w-4 h-4 text-indigo-500" />
                              <span className="font-medium">Avatar Video</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              {status.status === 'done' ? (
                                <CheckCircle className="w-4 h-4 text-green-500" />
                              ) : (
                                <Clock className="w-4 h-4 text-yellow-500" />
                              )}
                              <Badge variant={status.status === 'done' ? 'default' : 'secondary'}>
                                {status.status}
                              </Badge>
                            </div>
                          </div>
                          
                          {status.result_url && (
                            <div className="mt-4">
                              <video
                                controls
                                className="w-full max-w-md rounded-lg"
                                src={status.result_url}
                              >
                                Your browser does not support the video tag.
                              </video>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

export default App;