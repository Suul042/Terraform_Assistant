/**
 * Global state management using Zustand
 */
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { CloudProvider, ResourceType, ResourceParameter, GeneratedCode } from '@/lib/api';

// Types
interface GenerationState {
  provider: string;
  resourceType: string;
  action: string;
  naturalLanguageRequest: string;
  parameters: Record<string, any>;
  requirements: Record<string, any>;
  outputFormat: string[];
  includeComments: boolean;
}

interface UIState {
  sidebarOpen: boolean;
  rightPanelOpen: boolean;
  activeTab: string;
  loading: boolean;
  error: string | null;
}

interface AppStore {
  // UI State
  ui: UIState;
  setUI: (updates: Partial<UIState>) => void;
  
  // Providers
  providers: CloudProvider[];
  setProviders: (providers: CloudProvider[]) => void;
  selectedProvider: CloudProvider | null;
  setSelectedProvider: (provider: CloudProvider | null) => void;
  
  // Resource Types
  resourceTypes: ResourceType[];
  setResourceTypes: (types: ResourceType[]) => void;
  selectedResourceType: ResourceType | null;
  setSelectedResourceType: (type: ResourceType | null) => void;
  
  // Resource Parameters
  resourceParameters: ResourceParameter[];
  setResourceParameters: (params: ResourceParameter[]) => void;
  
  // Generation
  generation: GenerationState;
  setGeneration: (updates: Partial<GenerationState>) => void;
  generatedCode: GeneratedCode | null;
  setGeneratedCode: (code: GeneratedCode | null) => void;
  
  // Recent Generation History
  recentGenerations: GeneratedCode[];
  addToRecentGenerations: (code: GeneratedCode) => void;
  
  // Actions
  resetGeneration: () => void;
  clearError: () => void;
}

const initialGenerationState: GenerationState = {
  provider: 'aws',
  resourceType: '',
  action: 'create',
  naturalLanguageRequest: '',
  parameters: {},
  requirements: {},
  outputFormat: ['main'],
  includeComments: true,
};

const initialUIState: UIState = {
  sidebarOpen: true,
  rightPanelOpen: false,
  activeTab: 'generate',
  loading: false,
  error: null,
};

export const useAppStore = create<AppStore>()(
  devtools(
    (set, get) => ({
      // UI State
      ui: initialUIState,
      setUI: (updates) => set((state) => ({ ui: { ...state.ui, ...updates } })),
      
      // Providers
      providers: [],
      setProviders: (providers) => set({ providers }),
      selectedProvider: null,
      setSelectedProvider: (provider) => set({ selectedProvider: provider }),
      
      // Resource Types
      resourceTypes: [],
      setResourceTypes: (types) => set({ resourceTypes: types }),
      selectedResourceType: null,
      setSelectedResourceType: (type) => set({ selectedResourceType: type }),
      
      // Resource Parameters
      resourceParameters: [],
      setResourceParameters: (params) => set({ resourceParameters: params }),
      
      // Generation
      generation: initialGenerationState,
      setGeneration: (updates) => 
        set((state) => ({ generation: { ...state.generation, ...updates } })),
      generatedCode: null,
      setGeneratedCode: (code) => set({ generatedCode: code }),
      
      // Recent Generations
      recentGenerations: [],
      addToRecentGenerations: (code) => 
        set((state) => ({
          recentGenerations: [code, ...state.recentGenerations.slice(0, 9)] // Keep last 10
        })),
      
      // Actions
      resetGeneration: () => set({ 
        generation: initialGenerationState,
        generatedCode: null,
        selectedResourceType: null,
        resourceParameters: [],
      }),
      
      clearError: () => set((state) => ({ ui: { ...state.ui, error: null } })),
    }),
    {
      name: 'terraform-assistant-store',
    }
  )
);

// Selectors
export const useProviders = () => useAppStore((state) => state.providers);
export const useSelectedProvider = () => useAppStore((state) => state.selectedProvider);
export const useResourceTypes = () => useAppStore((state) => state.resourceTypes);
export const useSelectedResourceType = () => useAppStore((state) => state.selectedResourceType);
export const useResourceParameters = () => useAppStore((state) => state.resourceParameters);
export const useGeneration = () => useAppStore((state) => state.generation);
export const useGeneratedCode = () => useAppStore((state) => state.generatedCode);
export const useUI = () => useAppStore((state) => state.ui);
export const useRecentGenerations = () => useAppStore((state) => state.recentGenerations);

// Actions
export const useAppActions = () => useAppStore((state) => ({
  setUI: state.setUI,
  setProviders: state.setProviders,
  setSelectedProvider: state.setSelectedProvider,
  setResourceTypes: state.setResourceTypes,
  setSelectedResourceType: state.setSelectedResourceType,
  setResourceParameters: state.setResourceParameters,
  setGeneration: state.setGeneration,
  setGeneratedCode: state.setGeneratedCode,
  addToRecentGenerations: state.addToRecentGenerations,
  resetGeneration: state.resetGeneration,
  clearError: state.clearError,
}));