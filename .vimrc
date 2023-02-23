" Get the defaults that most users want.
source $VIMRUNTIME/defaults.vim

set laststatus=2

if &t_Co > 2 || has("gui_running")
  " Switch on highlighting the last used search pattern.
  set hlsearch
endif

" Put these in an autocmd group, so that we can delete them easily.
augroup vimrcEx
  au!
  " For all text files set 'textwidth' to 78 characters.
  autocmd FileType text setlocal textwidth=80
augroup END

set nocompatible              " be iMproved, required
filetype off                  " required

set rtp+=/opt/homebrew/opt/fzf

call plug#begin()
Plug 'itchyny/lightline.vim'
Plug 'preservim/nerdtree'
Plug 'tpope/vim-surround'
Plug 'tpope/vim-repeat'
Plug 'tpope/vim-endwise'
Plug 'airblade/vim-gitgutter'
Plug 'scrooloose/nerdcommenter'
Plug 'vim-syntastic/syntastic'
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'
Plug 'junegunn/vim-peekaboo'
Plug 'prettier/vim-prettier'
Plug 'chrisbra/Colorizer'
Plug 'ayu-theme/ayu-vim'
call plug#end()

filetype plugin indent on    " required

set termguicolors     " enable true colors support
syntax on

let ayucolor="dark"   " light | mirage | dark
colorscheme ayu

" Show hybrid line numbers
set number
set relativenumber
set hidden
set cursorline	      " highlight current line
set expandtab         " spaces not tabs
set tabstop=2
set autoindent
set copyindent
set expandtab
set shiftwidth=2
set smartindent
set smarttab
set softtabstop=2
set tabstop=2

" NERDTree
let mapleader=";"
map <Leader>n :NERDTreeToggle<CR>
map <Tab>   <C-W>w

" fzf search
nnoremap <leader>f :<C-u>FZF<CR>
nnoremap <leader>r :Rg<CR>

" Splits remap
nnoremap <C-J> <C-W><C-J>
nnoremap <C-K> <C-W><C-K>
nnoremap <C-L> <C-W><C-L>
nnoremap <C-H> <C-W><C-H>
set splitbelow
set splitright

" copy/paste remap
vnoremap <C-c> :w !pbcopy<CR><CR> 
noremap <C-v> :r !pbpaste<CR><CR>

" folding
set foldmethod=indent
set foldnestmax=10
set nofoldenable
set foldnestmax=2
