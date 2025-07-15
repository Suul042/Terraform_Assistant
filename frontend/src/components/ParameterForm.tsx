/**
 * Parameter Form Component
 */
import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { 
  InformationCircleIcon, 
  ExclamationTriangleIcon,
  PlusIcon,
  MinusIcon,
  ClipboardDocumentIcon
} from '@heroicons/react/24/outline';
import { ResourceParameter } from '@/lib/api';
import { useResourceParameters, useGeneration, useAppActions } from '@/store/app';
import { clsx } from 'clsx';

interface ParameterFormProps {
  onParametersChange?: (parameters: Record<string, any>) => void;
  disabled?: boolean;
}

// Dynamic form schema based on parameters
const createFormSchema = (parameters: ResourceParameter[]) => {
  const schema: Record<string, any> = {};
  
  parameters.forEach((param) => {
    let fieldSchema: any;
    
    switch (param.parameter_type) {
      case 'boolean':
        fieldSchema = z.boolean();
        break;
      case 'number':
        fieldSchema = z.number();
        break;
      case 'list':
        fieldSchema = z.array(z.string());
        break;
      case 'map':
        fieldSchema = z.record(z.string());
        break;
      default:
        fieldSchema = z.string();
    }
    
    if (param.is_required) {
      fieldSchema = fieldSchema.refine((val: any) => val !== undefined && val !== '', {
        message: `${param.parameter_name} is required`,
      });
    } else {
      fieldSchema = fieldSchema.optional();
    }
    
    schema[param.parameter_name] = fieldSchema;
  });
  
  return z.object(schema);
};

export default function ParameterForm({ onParametersChange, disabled = false }: ParameterFormProps) {
  const resourceParameters = useResourceParameters();
  const generation = useGeneration();
  const { setGeneration } = useAppActions();
  
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Create form schema
  const formSchema = createFormSchema(resourceParameters);
  
  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
    reset,
  } = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: generation.parameters,
    mode: 'onChange',
  });

  // Watch all form values
  const formValues = watch();

  // Update store when form values change
  useEffect(() => {
    if (isValid) {
      setGeneration({ parameters: formValues });
      onParametersChange?.(formValues);
    }
  }, [formValues, isValid, setGeneration, onParametersChange]);

  // Reset form when parameters change
  useEffect(() => {
    reset(generation.parameters);
  }, [resourceParameters, reset, generation.parameters]);

  const getParameterIcon = (paramType: string) => {
    const iconMap: Record<string, string> = {
      string: '📝',
      number: '🔢',
      boolean: '☑️',
      list: '📋',
      map: '🗺️',
    };
    return iconMap[paramType] || '📄';
  };

  const renderFormField = (param: ResourceParameter) => {
    const fieldName = param.parameter_name;
    const error = errors[fieldName];
    const fieldError = fieldErrors[fieldName];

    switch (param.parameter_type) {
      case 'boolean':
        return (
          <Controller
            name={fieldName}
            control={control}
            render={({ field }) => (
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id={fieldName}
                  checked={field.value || false}
                  onChange={field.onChange}
                  disabled={disabled}
                  className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <label htmlFor={fieldName} className="text-sm text-gray-700">
                  {param.is_required && <span className="text-red-500">*</span>}
                  {param.parameter_name}
                </label>
              </div>
            )}
          />
        );

      case 'number':
        return (
          <Controller
            name={fieldName}
            control={control}
            render={({ field }) => (
              <input
                type="number"
                id={fieldName}
                placeholder={param.example_value || `Enter ${param.parameter_name}`}
                value={field.value || ''}
                onChange={(e) => field.onChange(Number(e.target.value))}
                disabled={disabled}
                className={clsx(
                  'w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500',
                  error || fieldError
                    ? 'border-red-300 focus:border-red-500'
                    : 'border-gray-300 focus:border-primary-500'
                )}
              />
            )}
          />
        );

      case 'list':
        return (
          <Controller
            name={fieldName}
            control={control}
            render={({ field }) => (
              <ListInput
                value={field.value || []}
                onChange={field.onChange}
                disabled={disabled}
                placeholder={param.example_value || 'Add item'}
              />
            )}
          />
        );

      case 'map':
        return (
          <Controller
            name={fieldName}
            control={control}
            render={({ field }) => (
              <MapInput
                value={field.value || {}}
                onChange={field.onChange}
                disabled={disabled}
              />
            )}
          />
        );

      default:
        return (
          <Controller
            name={fieldName}
            control={control}
            render={({ field }) => (
              <input
                type="text"
                id={fieldName}
                placeholder={param.example_value || `Enter ${param.parameter_name}`}
                value={field.value || ''}
                onChange={field.onChange}
                disabled={disabled}
                className={clsx(
                  'w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500',
                  error || fieldError
                    ? 'border-red-300 focus:border-red-500'
                    : 'border-gray-300 focus:border-primary-500'
                )}
              />
            )}
          />
        );
    }
  };

  const requiredParams = resourceParameters.filter(p => p.is_required);
  const optionalParams = resourceParameters.filter(p => !p.is_required);

  if (resourceParameters.length === 0) {
    return (
      <div className="text-center py-8">
        <ClipboardDocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">No parameters available</h3>
        <p className="mt-1 text-sm text-gray-500">
          Select a resource type to configure its parameters.
        </p>
      </div>
    );
  }

  return (
    <div className={clsx('space-y-6', disabled && 'opacity-50 pointer-events-none')}>
      {/* Required Parameters */}
      {requiredParams.length > 0 && (
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Required Parameters
          </h3>
          <div className="space-y-4">
            {requiredParams.map((param) => (
              <div key={param.id} className="space-y-2">
                <div className="flex items-center space-x-2">
                  <span className="text-sm">{getParameterIcon(param.parameter_type || 'string')}</span>
                  <label className="block text-sm font-medium text-gray-700">
                    <span className="text-red-500">*</span> {param.parameter_name}
                  </label>
                  {param.parameter_type && (
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                      {param.parameter_type}
                    </span>
                  )}
                </div>
                
                {renderFormField(param)}
                
                {param.description && (
                  <div className="flex items-start space-x-2 text-sm text-gray-600">
                    <InformationCircleIcon className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <p>{param.description}</p>
                  </div>
                )}
                
                {(errors[param.parameter_name] || fieldErrors[param.parameter_name]) && (
                  <div className="flex items-center space-x-2 text-sm text-red-600">
                    <ExclamationTriangleIcon className="h-4 w-4" />
                    <span>
                      {errors[param.parameter_name]?.message || fieldErrors[param.parameter_name]}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Optional Parameters */}
      {optionalParams.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              Optional Parameters ({optionalParams.length})
            </h3>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-sm text-primary-600 hover:text-primary-800"
            >
              {showAdvanced ? 'Hide' : 'Show'} optional parameters
            </button>
          </div>
          
          {showAdvanced && (
            <div className="space-y-4">
              {optionalParams.map((param) => (
                <div key={param.id} className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm">{getParameterIcon(param.parameter_type || 'string')}</span>
                    <label className="block text-sm font-medium text-gray-700">
                      {param.parameter_name}
                    </label>
                    {param.parameter_type && (
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                        {param.parameter_type}
                      </span>
                    )}
                  </div>
                  
                  {renderFormField(param)}
                  
                  {param.description && (
                    <div className="flex items-start space-x-2 text-sm text-gray-600">
                      <InformationCircleIcon className="h-4 w-4 mt-0.5 flex-shrink-0" />
                      <p>{param.description}</p>
                    </div>
                  )}
                  
                  {(errors[param.parameter_name] || fieldErrors[param.parameter_name]) && (
                    <div className="flex items-center space-x-2 text-sm text-red-600">
                      <ExclamationTriangleIcon className="h-4 w-4" />
                      <span>
                        {errors[param.parameter_name]?.message || fieldErrors[param.parameter_name]}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Form Summary */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Configuration Summary</h4>
        <div className="text-sm text-gray-600">
          <p>Required: {requiredParams.length} parameters</p>
          <p>Optional: {optionalParams.length} parameters</p>
          <p>Configured: {Object.keys(formValues).length} parameters</p>
        </div>
      </div>
    </div>
  );
}

// List Input Component
function ListInput({ 
  value, 
  onChange, 
  disabled, 
  placeholder 
}: { 
  value: string[]; 
  onChange: (value: string[]) => void; 
  disabled: boolean; 
  placeholder: string; 
}) {
  const [newItem, setNewItem] = useState('');

  const addItem = () => {
    if (newItem.trim()) {
      onChange([...value, newItem.trim()]);
      setNewItem('');
    }
  };

  const removeItem = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <div className="flex space-x-2">
        <input
          type="text"
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          onKeyPress={(e) => e.key === 'Enter' && addItem()}
        />
        <button
          type="button"
          onClick={addItem}
          disabled={disabled || !newItem.trim()}
          className="px-3 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
        >
          <PlusIcon className="h-4 w-4" />
        </button>
      </div>
      
      {value.length > 0 && (
        <div className="space-y-1">
          {value.map((item, index) => (
            <div key={index} className="flex items-center space-x-2 bg-gray-50 px-3 py-2 rounded">
              <span className="flex-1 text-sm">{item}</span>
              <button
                type="button"
                onClick={() => removeItem(index)}
                disabled={disabled}
                className="text-red-500 hover:text-red-700 disabled:opacity-50"
              >
                <MinusIcon className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Map Input Component
function MapInput({ 
  value, 
  onChange, 
  disabled 
}: { 
  value: Record<string, string>; 
  onChange: (value: Record<string, string>) => void; 
  disabled: boolean; 
}) {
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');

  const addPair = () => {
    if (newKey.trim() && newValue.trim()) {
      onChange({ ...value, [newKey.trim()]: newValue.trim() });
      setNewKey('');
      setNewValue('');
    }
  };

  const removePair = (key: string) => {
    const newValue = { ...value };
    delete newValue[key];
    onChange(newValue);
  };

  return (
    <div className="space-y-2">
      <div className="flex space-x-2">
        <input
          type="text"
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          placeholder="Key"
          disabled={disabled}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
        <input
          type="text"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          placeholder="Value"
          disabled={disabled}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
        <button
          type="button"
          onClick={addPair}
          disabled={disabled || !newKey.trim() || !newValue.trim()}
          className="px-3 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
        >
          <PlusIcon className="h-4 w-4" />
        </button>
      </div>
      
      {Object.entries(value).length > 0 && (
        <div className="space-y-1">
          {Object.entries(value).map(([key, val]) => (
            <div key={key} className="flex items-center space-x-2 bg-gray-50 px-3 py-2 rounded">
              <span className="flex-1 text-sm font-medium">{key}:</span>
              <span className="flex-1 text-sm">{val}</span>
              <button
                type="button"
                onClick={() => removePair(key)}
                disabled={disabled}
                className="text-red-500 hover:text-red-700 disabled:opacity-50"
              >
                <MinusIcon className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}